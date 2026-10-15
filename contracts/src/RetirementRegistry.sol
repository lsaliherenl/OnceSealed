// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {
    AccessControlDefaultAdminRules
} from "@openzeppelin/contracts/access/extensions/AccessControlDefaultAdminRules.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

/// @title RetirementRegistry
/// @notice Proof registry for carbon credit retirements: each credit serial can be retired once,
///         the buyer is recorded only as a salted commitment, and an auditor can attest each retirement.
/// @dev Prototype of a verification layer on top of existing registries. It performs no real
///      retirements and never mints tokens: retired credits must not become tradable again.
///      Admin handover is two-step with a delay (AccessControlDefaultAdminRules), so a single
///      mistaken or stolen transaction cannot hand over the registry.
///      Privacy against amount matching: a batch registered with a lot size only accepts retirements of
///      exactly one aligned lot (the batch's final lot may be shorter), so every private retirement in it
///      looks the same on-chain. Free-range batches (lot size 0) accept any range.
contract RetirementRegistry is AccessControlDefaultAdminRules {
    bytes32 public constant ASSESSOR_ROLE = keccak256("ASSESSOR_ROLE");
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");

    enum AuditStatus {
        Pending,
        Verified,
        Rejected
    }

    struct Batch {
        bytes32 projectId;
        uint64 firstSerial;
        uint64 lastSerial;
        uint64 lotSize; // 0 = free ranges; otherwise every retirement is exactly one aligned lot
        bool exists;
    }

    struct QualityReport {
        bytes32 reportHash; // keccak256 of the published report's canonical JSON
        bytes32 methodHash; // pins the models, prompt and question set that produced it
        uint16 score; // 0-100 evidence signal, not an ICVCM verdict
        uint64 registeredAt;
    }

    struct Retirement {
        bytes32 batchId;
        uint64 start;
        uint64 end;
        bytes32 buyerCommitment;
        bytes32 auditVaultHash; // keccak256 of the auditor-encrypted vault, stored off-chain
        uint32 reportVersion; // project's quality report version at retirement time; 0 = none yet
        uint64 retiredAt;
        AuditStatus audit;
    }

    mapping(bytes32 batchId => Batch) private _batches;
    mapping(bytes32 batchId => uint256[]) private _batchRetirements;
    mapping(bytes32 projectId => QualityReport[]) private _reports;
    mapping(uint256 retirementId => Retirement) private _retirements;
    // Retirements of a batch as a linked list sorted by serial: head = lowest range.
    mapping(bytes32 batchId => uint256) private _head;
    mapping(uint256 retirementId => uint256) private _next;
    // Lot batches: lot index -> retirement id (constant-time overlap check and lookup, no list needed).
    mapping(bytes32 batchId => mapping(uint64 lotIndex => uint256)) private _lotRetirement;
    uint256 public retirementCount; // ids start at 1

    event BatchRegistered(
        bytes32 indexed batchId, bytes32 indexed projectId, uint64 firstSerial, uint64 lastSerial, uint64 lotSize
    );
    event QualityReportRegistered(
        bytes32 indexed projectId, uint32 indexed version, bytes32 reportHash, bytes32 methodHash, uint16 score
    );
    event CreditRetired(
        uint256 indexed retirementId,
        bytes32 indexed batchId,
        bytes32 indexed projectId,
        uint64 start,
        uint64 end,
        bytes32 buyerCommitment,
        bytes32 auditVaultHash,
        uint32 reportVersion
    );
    event RetirementAttested(uint256 indexed retirementId, bool valid, address indexed auditor);

    error BatchExists(bytes32 batchId);
    error UnknownBatch(bytes32 batchId);
    error InvalidRange(uint64 start, uint64 end);
    error AlreadyRetired(uint256 conflictingRetirementId);
    error InvalidScore(uint16 score);
    error ZeroValue();
    error UnknownRetirement(uint256 retirementId);
    error AlreadyAttested(uint256 retirementId);
    error UnknownReport(bytes32 projectId, uint32 version);
    error InvalidHint(uint256 prevHint);
    error NotALot(uint64 start, uint64 end, uint64 lotSize);

    /// @param adminDelay seconds a scheduled admin handover must wait before it can be accepted
    constructor(uint48 adminDelay, address admin) AccessControlDefaultAdminRules(adminDelay, admin) {}

    // ---------------------------------------------------------------------------------------------
    // Writes
    // ---------------------------------------------------------------------------------------------

    /// @notice Declare an issuance batch and its serial range. Retirements must fall inside it.
    /// @param lotSize 0 for free ranges, or the standard lot size every retirement in this batch must have.
    function registerBatch(bytes32 batchId, bytes32 projectId, uint64 firstSerial, uint64 lastSerial, uint64 lotSize)
        external
        onlyRole(OPERATOR_ROLE)
    {
        if (batchId == bytes32(0) || projectId == bytes32(0)) revert ZeroValue();
        if (firstSerial > lastSerial) revert InvalidRange(firstSerial, lastSerial);
        if (_batches[batchId].exists) revert BatchExists(batchId);
        _batches[batchId] = Batch(projectId, firstSerial, lastSerial, lotSize, true);
        emit BatchRegistered(batchId, projectId, firstSerial, lastSerial, lotSize);
    }

    /// @notice Anchor a new version of a project's quality report. Earlier versions are kept.
    function registerQualityReport(bytes32 projectId, bytes32 reportHash, uint16 score, bytes32 methodHash)
        external
        onlyRole(ASSESSOR_ROLE)
        returns (uint32 version)
    {
        if (projectId == bytes32(0) || reportHash == bytes32(0) || methodHash == bytes32(0)) {
            revert ZeroValue();
        }
        if (score > 100) revert InvalidScore(score);
        _reports[projectId].push(QualityReport(reportHash, methodHash, score, SafeCast.toUint64(block.timestamp)));
        version = SafeCast.toUint32(_reports[projectId].length);
        emit QualityReportRegistered(projectId, version, reportHash, methodHash, score);
    }

    /// @notice Retire serials [start, end] of a batch. Reverts if any serial in the range was retired before.
    /// @param buyerCommitment keccak256(abi.encode(buyerId, salt, batchId, start, end)); see commitmentOf.
    /// @param prevHint free-range batches: id of the batch's retirement that ends right before `start`, or 0 if
    ///        the new range comes first (clients get it from hintFor() or CreditRetired events). Ignored for
    ///        lot batches, where the lot index is checked directly.
    /// @dev Retirements of a batch form a sorted, non-overlapping linked list. Given the immediate predecessor,
    ///      checking the two neighbours proves the new range overlaps nothing, so gas stays constant however
    ///      many retirements the batch has (a linear scan reached the block gas limit at a few thousand).
    ///      A wrong hint can only make the call revert; it can never let an overlapping range in.
    function retire(
        bytes32 batchId,
        uint64 start,
        uint64 end,
        bytes32 buyerCommitment,
        bytes32 auditVaultHash,
        uint256 prevHint
    ) external onlyRole(OPERATOR_ROLE) returns (uint256 retirementId) {
        Batch storage batch = _batches[batchId];
        if (!batch.exists) revert UnknownBatch(batchId);
        if (start > end || start < batch.firstSerial || end > batch.lastSerial) revert InvalidRange(start, end);
        if (buyerCommitment == bytes32(0) || auditVaultHash == bytes32(0)) revert ZeroValue();

        if (batch.lotSize != 0) {
            retirementId = _retireLot(batchId, batch, start, end);
        } else {
            retirementId = _retireRange(batchId, start, end, prevHint);
        }
        uint32 reportVersion = SafeCast.toUint32(_reports[batch.projectId].length);
        _retirements[retirementId] = Retirement({
            batchId: batchId,
            start: start,
            end: end,
            buyerCommitment: buyerCommitment,
            auditVaultHash: auditVaultHash,
            reportVersion: reportVersion,
            retiredAt: SafeCast.toUint64(block.timestamp),
            audit: AuditStatus.Pending
        });
        _batchRetirements[batchId].push(retirementId);
        emit CreditRetired(
            retirementId, batchId, batch.projectId, start, end, buyerCommitment, auditVaultHash, reportVersion
        );
    }

    /// @dev One aligned lot; only the batch's final lot may be shorter than lotSize.
    function _retireLot(bytes32 batchId, Batch storage batch, uint64 start, uint64 end)
        private
        returns (uint256 retirementId)
    {
        uint64 lot = batch.lotSize;
        uint64 offset = start - batch.firstSerial;
        uint64 size = end - start + 1;
        if (offset % lot != 0 || (size != lot && !(size < lot && end == batch.lastSerial))) {
            revert NotALot(start, end, lot);
        }
        uint64 index = offset / lot;
        uint256 existing = _lotRetirement[batchId][index];
        if (existing != 0) revert AlreadyRetired(existing);
        retirementId = ++retirementCount;
        _lotRetirement[batchId][index] = retirementId;
    }

    /// @dev Insert into the batch's sorted list after checking the hinted neighbours.
    function _retireRange(bytes32 batchId, uint64 start, uint64 end, uint256 prevHint)
        private
        returns (uint256 retirementId)
    {
        uint256 next;
        if (prevHint == 0) {
            next = _head[batchId];
        } else {
            Retirement storage p = _retirements[prevHint];
            if (p.retiredAt == 0 || p.batchId != batchId) revert InvalidHint(prevHint);
            if (p.end >= start) {
                if (p.start <= end) revert AlreadyRetired(prevHint);
                revert InvalidHint(prevHint); // the hinted retirement lies after the new range
            }
            next = _next[prevHint];
        }
        if (next != 0) {
            Retirement storage n = _retirements[next];
            if (n.start <= end) {
                if (start <= n.end) revert AlreadyRetired(next);
                revert InvalidHint(prevHint); // the hint is not the immediate predecessor
            }
        }

        retirementId = ++retirementCount;
        _next[retirementId] = next;
        if (prevHint == 0) _head[batchId] = retirementId;
        else _next[prevHint] = retirementId;
    }

    /// @notice Record the auditor's off-chain check of the vault against the commitment. One-time and final.
    function attestRetirement(uint256 retirementId, bool valid) external onlyRole(AUDITOR_ROLE) {
        Retirement storage r = _existing(retirementId);
        if (r.audit != AuditStatus.Pending) revert AlreadyAttested(retirementId);
        r.audit = valid ? AuditStatus.Verified : AuditStatus.Rejected;
        emit RetirementAttested(retirementId, valid, msg.sender);
    }

    // ---------------------------------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------------------------------

    /// @notice The commitment binds the buyer to this exact range, so a disclosed salt proves one
    ///         retirement and cannot be reused to claim another.
    function commitmentOf(bytes32 buyerId, bytes32 salt, bytes32 batchId, uint64 start, uint64 end)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(buyerId, salt, batchId, start, end));
    }

    /// @notice Selective disclosure: true if (buyerId, salt) opens the retirement's commitment.
    function verifyClaim(uint256 retirementId, bytes32 buyerId, bytes32 salt) external view returns (bool) {
        Retirement storage r = _existing(retirementId);
        return commitmentOf(buyerId, salt, r.batchId, r.start, r.end) == r.buyerCommitment;
    }

    function getRetirement(uint256 retirementId) external view returns (Retirement memory) {
        return _existing(retirementId);
    }

    function getBatch(bytes32 batchId) external view returns (Batch memory) {
        if (!_batches[batchId].exists) revert UnknownBatch(batchId);
        return _batches[batchId];
    }

    function batchRetirements(bytes32 batchId) external view returns (uint256[] memory) {
        return _batchRetirements[batchId];
    }

    /// @notice Returns the retirement id covering `serial`, or 0 if it has not been retired.
    /// @dev Constant time for lot batches; walks the sorted list for free-range batches (off-chain reads).
    function retirementOf(bytes32 batchId, uint64 serial) public view returns (uint256) {
        Batch storage b = _batches[batchId];
        if (b.lotSize != 0) {
            if (serial < b.firstSerial || serial > b.lastSerial) return 0;
            return _lotRetirement[batchId][(serial - b.firstSerial) / b.lotSize];
        }
        for (uint256 id = _head[batchId]; id != 0; id = _next[id]) {
            Retirement storage r = _retirements[id];
            if (serial < r.start) return 0;
            if (serial <= r.end) return id;
        }
        return 0;
    }

    /// @notice The prevHint to pass to retire() for a range starting at `start`: the last retirement in the
    ///         batch that starts before it (0 if none). If that retirement overlaps, retire() reports it.
    /// @dev Walks the sorted list; for very large batches compute the hint off-chain from CreditRetired events.
    function hintFor(bytes32 batchId, uint64 start) external view returns (uint256 prev) {
        for (uint256 id = _head[batchId]; id != 0; id = _next[id]) {
            if (_retirements[id].start >= start) break;
            prev = id;
        }
    }

    /// @notice Retirement ids of a free-range batch in serial order (empty for lot batches; see batchRetirements).
    function orderedRetirements(bytes32 batchId) external view returns (uint256[] memory out) {
        out = new uint256[](_batchRetirements[batchId].length);
        uint256 i = 0;
        for (uint256 id = _head[batchId]; id != 0; id = _next[id]) {
            out[i++] = id;
        }
        assembly ("memory-safe") {
            mstore(out, i)
        }
    }

    function isRetired(bytes32 batchId, uint64 serial) external view returns (bool) {
        return retirementOf(batchId, serial) != 0;
    }

    function reportCount(bytes32 projectId) external view returns (uint32) {
        return SafeCast.toUint32(_reports[projectId].length);
    }

    /// @param version 1-based report version.
    function getReport(bytes32 projectId, uint32 version) public view returns (QualityReport memory) {
        if (version == 0 || version > _reports[projectId].length) revert UnknownReport(projectId, version);
        return _reports[projectId][version - 1];
    }

    function latestReport(bytes32 projectId) external view returns (QualityReport memory) {
        return getReport(projectId, SafeCast.toUint32(_reports[projectId].length));
    }

    function _existing(uint256 retirementId) private view returns (Retirement storage r) {
        r = _retirements[retirementId];
        if (r.retiredAt == 0) revert UnknownRetirement(retirementId);
    }
}
