// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

/// @title RetirementRegistry
/// @notice Proof registry for carbon credit retirements: each credit serial can be retired once,
///         the buyer is recorded only as a salted commitment, and an auditor can attest each retirement.
/// @dev Prototype of a verification layer on top of existing registries. It performs no real
///      retirements and never mints tokens: retired credits must not become tradable again.
contract RetirementRegistry is AccessControl {
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
    uint256 public retirementCount; // ids start at 1

    event BatchRegistered(bytes32 indexed batchId, bytes32 indexed projectId, uint64 firstSerial, uint64 lastSerial);
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

    constructor(address admin) {
        if (admin == address(0)) revert ZeroValue();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    // ---------------------------------------------------------------------------------------------
    // Writes
    // ---------------------------------------------------------------------------------------------

    /// @notice Declare an issuance batch and its serial range. Retirements must fall inside it.
    function registerBatch(bytes32 batchId, bytes32 projectId, uint64 firstSerial, uint64 lastSerial)
        external
        onlyRole(OPERATOR_ROLE)
    {
        if (batchId == bytes32(0) || projectId == bytes32(0)) revert ZeroValue();
        if (firstSerial > lastSerial) revert InvalidRange(firstSerial, lastSerial);
        if (_batches[batchId].exists) revert BatchExists(batchId);
        _batches[batchId] = Batch(projectId, firstSerial, lastSerial, true);
        emit BatchRegistered(batchId, projectId, firstSerial, lastSerial);
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
    /// @dev Overlap check is a linear scan over the batch's retirements: fine for a prototype, and only the
    ///      operator can add entries. A production registry would keep an ordered interval structure.
    function retire(bytes32 batchId, uint64 start, uint64 end, bytes32 buyerCommitment, bytes32 auditVaultHash)
        external
        onlyRole(OPERATOR_ROLE)
        returns (uint256 retirementId)
    {
        Batch storage batch = _batches[batchId];
        if (!batch.exists) revert UnknownBatch(batchId);
        if (start > end || start < batch.firstSerial || end > batch.lastSerial) revert InvalidRange(start, end);
        if (buyerCommitment == bytes32(0) || auditVaultHash == bytes32(0)) revert ZeroValue();

        uint256[] storage ids = _batchRetirements[batchId];
        for (uint256 i = 0; i < ids.length; ++i) {
            Retirement storage r = _retirements[ids[i]];
            // Reverting inside the loop is intended: any intersection with a past retirement is fatal.
            // forge-lint: disable-next-line(require-revert-in-loop)
            if (start <= r.end && r.start <= end) revert AlreadyRetired(ids[i]);
        }

        retirementId = ++retirementCount;
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
        ids.push(retirementId);
        emit CreditRetired(
            retirementId, batchId, batch.projectId, start, end, buyerCommitment, auditVaultHash, reportVersion
        );
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
    function retirementOf(bytes32 batchId, uint64 serial) public view returns (uint256) {
        uint256[] storage ids = _batchRetirements[batchId];
        for (uint256 i = 0; i < ids.length; ++i) {
            Retirement storage r = _retirements[ids[i]];
            if (r.start <= serial && serial <= r.end) return ids[i];
        }
        return 0;
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
