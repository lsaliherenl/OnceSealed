// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {RetirementRegistry} from "../src/RetirementRegistry.sol";

contract RetirementRegistryTest is Test {
    RetirementRegistry internal reg;

    address internal admin = makeAddr("admin");
    address internal assessor = makeAddr("assessor");
    address internal operator = makeAddr("operator");
    address internal auditor = makeAddr("auditor");
    address internal stranger = makeAddr("stranger");

    bytes32 internal constant PROJECT = keccak256("VCS1477");
    bytes32 internal constant BATCH = keccak256("VCS1477|batch-1");
    bytes32 internal constant BATCH_2 = keccak256("VCS1477|batch-2");
    uint64 internal constant FIRST = 1;
    uint64 internal constant LAST = 1000;

    bytes32 internal constant BUYER = keccak256("LEI:529900T8BM49AURSDO55");
    bytes32 internal constant SALT = keccak256("salt-1");
    bytes32 internal constant VAULT = keccak256("vault-ciphertext");
    bytes32 internal constant REPORT = keccak256("report-v1");
    bytes32 internal constant METHOD = keccak256("method-v1");

    function setUp() public {
        reg = new RetirementRegistry(admin);
        vm.startPrank(admin);
        reg.grantRole(reg.ASSESSOR_ROLE(), assessor);
        reg.grantRole(reg.OPERATOR_ROLE(), operator);
        reg.grantRole(reg.AUDITOR_ROLE(), auditor);
        vm.stopPrank();

        vm.prank(operator);
        reg.registerBatch(BATCH, PROJECT, FIRST, LAST);
    }

    function _retire(uint64 start, uint64 end) internal returns (uint256) {
        return _retire(BATCH, start, end);
    }

    function _retire(bytes32 batchId, uint64 start, uint64 end) internal returns (uint256) {
        bytes32 c = reg.commitmentOf(BUYER, SALT, batchId, start, end);
        vm.prank(operator);
        return reg.retire(batchId, start, end, c, VAULT);
    }

    function _expectRetireRevert(uint64 start, uint64 end, bytes memory err) internal {
        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, start, end);
        vm.prank(operator);
        vm.expectRevert(err);
        reg.retire(BATCH, start, end, c, VAULT);
    }

    // --- batches ------------------------------------------------------------------------------

    function test_RegisterBatch() public view {
        RetirementRegistry.Batch memory b = reg.getBatch(BATCH);
        assertEq(b.projectId, PROJECT);
        assertEq(b.firstSerial, FIRST);
        assertEq(b.lastSerial, LAST);
    }

    function test_RevertWhen_BatchRegisteredTwice() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.BatchExists.selector, BATCH));
        reg.registerBatch(BATCH, PROJECT, 1, 10);
    }

    function test_RevertWhen_BatchRangeInverted() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.InvalidRange.selector, 10, 5));
        reg.registerBatch(BATCH_2, PROJECT, 10, 5);
    }

    // --- retirement and double counting ---------------------------------------------------------

    function test_RetireStoresRecordAndEmits() public {
        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, 100, 199);
        vm.expectEmit(true, true, true, true);
        emit RetirementRegistry.CreditRetired(1, BATCH, PROJECT, 100, 199, c, VAULT, 0);
        vm.prank(operator);
        uint256 id = reg.retire(BATCH, 100, 199, c, VAULT);

        assertEq(id, 1);
        RetirementRegistry.Retirement memory r = reg.getRetirement(id);
        assertEq(r.batchId, BATCH);
        assertEq(r.start, 100);
        assertEq(r.end, 199);
        assertEq(r.buyerCommitment, c);
        assertEq(r.auditVaultHash, VAULT);
        assertEq(uint8(r.audit), uint8(RetirementRegistry.AuditStatus.Pending));
        assertTrue(reg.isRetired(BATCH, 150));
        assertFalse(reg.isRetired(BATCH, 200));
    }

    function test_RevertWhen_SameRangeRetiredTwice() public {
        _retire(100, 199);
        _expectRetireRevert(100, 199, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
    }

    function test_RevertWhen_PartialOverlap() public {
        _retire(100, 199);
        _expectRetireRevert(50, 100, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
        _expectRetireRevert(199, 250, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
    }

    function test_RevertWhen_RangeContainedOrContaining() public {
        _retire(100, 199);
        _expectRetireRevert(120, 130, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
        _expectRetireRevert(1, 1000, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
    }

    function test_ReportsTheConflictingRetirement() public {
        _retire(1, 99);
        _retire(100, 199);
        _expectRetireRevert(150, 160, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 2));
    }

    function test_AdjacentRangesAllowed() public {
        assertEq(_retire(100, 199), 1);
        assertEq(_retire(200, 299), 2);
        assertEq(_retire(99, 99), 3);
        assertEq(reg.batchRetirements(BATCH).length, 3);
    }

    function test_SameSerialsInAnotherBatchAllowed() public {
        vm.prank(operator);
        reg.registerBatch(BATCH_2, PROJECT, FIRST, LAST);
        _retire(BATCH, 100, 199);
        assertEq(_retire(BATCH_2, 100, 199), 2);
    }

    function test_RevertWhen_OutsideBatchOrInverted() public {
        _expectRetireRevert(0, 10, abi.encodeWithSelector(RetirementRegistry.InvalidRange.selector, 0, 10));
        _expectRetireRevert(990, 1001, abi.encodeWithSelector(RetirementRegistry.InvalidRange.selector, 990, 1001));
        _expectRetireRevert(20, 10, abi.encodeWithSelector(RetirementRegistry.InvalidRange.selector, 20, 10));
    }

    function test_RevertWhen_UnknownBatch() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.UnknownBatch.selector, BATCH_2));
        reg.retire(BATCH_2, 1, 10, keccak256("c"), VAULT);
    }

    function test_RevertWhen_ZeroCommitmentOrVault() public {
        vm.startPrank(operator);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.retire(BATCH, 1, 10, bytes32(0), VAULT);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.retire(BATCH, 1, 10, keccak256("c"), bytes32(0));
        vm.stopPrank();
    }

    /// Any two ranges in the same batch: the second retirement succeeds exactly when they do not intersect.
    function testFuzz_SecondRetirementRevertsIffOverlap(uint64 a1, uint64 b1, uint64 a2, uint64 b2) public {
        a1 = uint64(bound(a1, FIRST, LAST));
        b1 = uint64(bound(b1, a1, LAST));
        a2 = uint64(bound(a2, FIRST, LAST));
        b2 = uint64(bound(b2, a2, LAST));
        _retire(a1, b1);

        bool overlap = a2 <= b1 && a1 <= b2;
        if (overlap) {
            _expectRetireRevert(a2, b2, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
        } else {
            assertEq(_retire(a2, b2), 2);
        }
    }

    /// Every serial is covered by at most one retirement, whatever order ranges arrive in.
    function testFuzz_NoSerialRetiredTwice(uint64[6] memory starts, uint64[6] memory lens, uint64 probe) public {
        for (uint256 i = 0; i < 6; ++i) {
            uint64 s = uint64(bound(starts[i], FIRST, LAST));
            uint64 e = uint64(bound(lens[i], 0, 200)) + s;
            if (e > LAST) e = LAST;
            bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, s, e);
            vm.prank(operator);
            try reg.retire(BATCH, s, e, c, VAULT) {} catch {}
        }
        probe = uint64(bound(probe, FIRST, LAST));
        uint256[] memory ids = reg.batchRetirements(BATCH);
        uint256 covering;
        for (uint256 i = 0; i < ids.length; ++i) {
            RetirementRegistry.Retirement memory r = reg.getRetirement(ids[i]);
            if (r.start <= probe && probe <= r.end) covering++;
        }
        assertLe(covering, 1);
        assertEq(covering == 1, reg.isRetired(BATCH, probe));
    }

    // --- selective disclosure -----------------------------------------------------------------

    function test_VerifyClaim() public {
        uint256 id = _retire(100, 199);
        assertTrue(reg.verifyClaim(id, BUYER, SALT));
        assertFalse(reg.verifyClaim(id, BUYER, keccak256("wrong-salt")));
        assertFalse(reg.verifyClaim(id, keccak256("LEI:OTHER"), SALT));
    }

    function test_DisclosedSaltCannotClaimAnotherRetirement() public {
        uint256 first = _retire(100, 199);
        // Even if the same commitment were copied onto a different range, the claim would not verify.
        bytes32 copied = reg.getRetirement(first).buyerCommitment;
        vm.prank(operator);
        uint256 second = reg.retire(BATCH, 300, 399, copied, VAULT);
        assertTrue(reg.verifyClaim(first, BUYER, SALT));
        assertFalse(reg.verifyClaim(second, BUYER, SALT));
    }

    function test_RevertWhen_UnknownRetirement() public {
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.UnknownRetirement.selector, 42));
        reg.verifyClaim(42, BUYER, SALT);
    }

    // --- quality reports ----------------------------------------------------------------------

    function test_QualityReportsAreVersioned() public {
        vm.startPrank(assessor);
        assertEq(reg.registerQualityReport(PROJECT, REPORT, 64, METHOD), 1);
        assertEq(reg.registerQualityReport(PROJECT, keccak256("report-v2"), 57, METHOD), 2);
        vm.stopPrank();

        assertEq(reg.reportCount(PROJECT), 2);
        assertEq(reg.getReport(PROJECT, 1).reportHash, REPORT);
        assertEq(reg.getReport(PROJECT, 1).score, 64);
        assertEq(reg.latestReport(PROJECT).score, 57);
    }

    function test_RevertWhen_ScoreAbove100() public {
        vm.prank(assessor);
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.InvalidScore.selector, 101));
        reg.registerQualityReport(PROJECT, REPORT, 101, METHOD);
    }

    function test_RevertWhen_ReportMissingHashes() public {
        vm.startPrank(assessor);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.registerQualityReport(PROJECT, bytes32(0), 50, METHOD);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.registerQualityReport(PROJECT, REPORT, 50, bytes32(0));
        vm.stopPrank();
    }

    function test_RevertWhen_UnknownReportVersion() public {
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.UnknownReport.selector, PROJECT, 0));
        reg.latestReport(PROJECT);
    }

    function test_RetirementRecordsReportVersionAtThatTime() public {
        uint256 before = _retire(1, 10);
        vm.prank(assessor);
        reg.registerQualityReport(PROJECT, REPORT, 64, METHOD);
        uint256 afterFirst = _retire(11, 20);
        vm.prank(assessor);
        reg.registerQualityReport(PROJECT, keccak256("report-v2"), 57, METHOD);

        assertEq(reg.getRetirement(before).reportVersion, 0);
        assertEq(reg.getRetirement(afterFirst).reportVersion, 1);
        assertEq(reg.getReport(PROJECT, reg.getRetirement(afterFirst).reportVersion).score, 64);
    }

    // --- audit --------------------------------------------------------------------------------

    function test_AttestRetirement() public {
        uint256 id = _retire(100, 199);
        vm.expectEmit(true, true, false, true);
        emit RetirementRegistry.RetirementAttested(id, true, auditor);
        vm.prank(auditor);
        reg.attestRetirement(id, true);
        assertEq(uint8(reg.getRetirement(id).audit), uint8(RetirementRegistry.AuditStatus.Verified));
    }

    function test_AttestationIsFinal() public {
        uint256 id = _retire(100, 199);
        vm.startPrank(auditor);
        reg.attestRetirement(id, false);
        vm.expectRevert(abi.encodeWithSelector(RetirementRegistry.AlreadyAttested.selector, id));
        reg.attestRetirement(id, true);
        vm.stopPrank();
        assertEq(uint8(reg.getRetirement(id).audit), uint8(RetirementRegistry.AuditStatus.Rejected));
    }

    // --- access control -----------------------------------------------------------------------

    function _expectUnauthorized(address account, bytes32 role) internal {
        vm.expectRevert(abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, account, role));
    }

    function test_RevertWhen_CallerLacksRole() public {
        // Read role ids before vm.prank: a getter call would consume the prank.
        bytes32 operatorRole = reg.OPERATOR_ROLE();
        bytes32 assessorRole = reg.ASSESSOR_ROLE();
        bytes32 auditorRole = reg.AUDITOR_ROLE();
        uint256 id = _retire(1, 10);

        vm.prank(stranger);
        _expectUnauthorized(stranger, operatorRole);
        reg.retire(BATCH, 20, 30, keccak256("c"), VAULT);

        vm.prank(assessor);
        _expectUnauthorized(assessor, operatorRole);
        reg.registerBatch(BATCH_2, PROJECT, 1, 10);

        vm.prank(operator);
        _expectUnauthorized(operator, assessorRole);
        reg.registerQualityReport(PROJECT, REPORT, 50, METHOD);

        vm.prank(operator);
        _expectUnauthorized(operator, auditorRole);
        reg.attestRetirement(id, true);
    }

    function test_OnlyAdminGrantsRoles() public {
        bytes32 operatorRole = reg.OPERATOR_ROLE();
        bytes32 adminRole = reg.DEFAULT_ADMIN_ROLE();
        vm.prank(operator);
        _expectUnauthorized(operator, adminRole);
        reg.grantRole(operatorRole, stranger);
    }
}
