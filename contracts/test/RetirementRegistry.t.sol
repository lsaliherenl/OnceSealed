// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {
    IAccessControlDefaultAdminRules
} from "@openzeppelin/contracts/access/extensions/IAccessControlDefaultAdminRules.sol";
import {RetirementRegistry} from "../src/RetirementRegistry.sol";

contract RetirementRegistryTest is Test {
    RetirementRegistry internal reg;

    address internal admin = makeAddr("admin");
    address internal assessor = makeAddr("assessor");
    address internal operator = makeAddr("operator");
    address internal auditor = makeAddr("auditor");
    address internal stranger = makeAddr("stranger");

    uint48 internal constant ADMIN_DELAY = 2 days;
    bytes32 internal constant PROJECT = keccak256("VCS1477");
    bytes32 internal constant BATCH = keccak256("VCS1477|batch-1");
    bytes32 internal constant BATCH_2 = keccak256("VCS1477|batch-2");
    uint64 internal constant FIRST = 1;
    uint64 internal constant LAST = 1000;

    bytes32 internal constant BUYER = keccak256("LEI:ONCE00SEALEDDEMO0143");
    bytes32 internal constant SALT = keccak256("salt-1");
    bytes32 internal constant VAULT = keccak256("vault-ciphertext");
    bytes32 internal constant REPORT = keccak256("report-v1");
    bytes32 internal constant METHOD = keccak256("method-v1");

    function setUp() public {
        reg = new RetirementRegistry(ADMIN_DELAY, admin);
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

    /// Retire with the correct hint, computed before vm.prank (a view call would consume the prank).
    function _retire(bytes32 batchId, uint64 start, uint64 end) internal returns (uint256) {
        bytes32 c = reg.commitmentOf(BUYER, SALT, batchId, start, end);
        uint256 hint = reg.hintFor(batchId, start);
        vm.prank(operator);
        return reg.retire(batchId, start, end, c, VAULT, hint);
    }

    function _retireWithHint(uint64 start, uint64 end, uint256 hint) internal returns (uint256) {
        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, start, end);
        vm.prank(operator);
        return reg.retire(BATCH, start, end, c, VAULT, hint);
    }

    function _expectRetireRevert(uint64 start, uint64 end, bytes memory err) internal {
        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, start, end);
        uint256 hint = reg.hintFor(BATCH, start);
        vm.prank(operator);
        vm.expectRevert(err);
        reg.retire(BATCH, start, end, c, VAULT, hint);
    }

    function _expectHintRevert(uint64 start, uint64 end, uint256 hint, bytes memory err) internal {
        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, start, end);
        vm.prank(operator);
        vm.expectRevert(err);
        reg.retire(BATCH, start, end, c, VAULT, hint);
    }

    function _assertSortedAndDisjoint(bytes32 batchId) internal view {
        uint256[] memory ids = reg.orderedRetirements(batchId);
        assertEq(ids.length, reg.batchRetirements(batchId).length, "list covers all retirements");
        for (uint256 i = 1; i < ids.length; ++i) {
            assertLt(reg.getRetirement(ids[i - 1]).end, reg.getRetirement(ids[i]).start, "sorted and disjoint");
        }
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
        uint256 id = reg.retire(BATCH, 100, 199, c, VAULT, 0);

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
        _assertSortedAndDisjoint(BATCH);
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
        reg.retire(BATCH_2, 1, 10, keccak256("c"), VAULT, 0);
    }

    function test_RevertWhen_ZeroCommitmentOrVault() public {
        vm.startPrank(operator);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.retire(BATCH, 1, 10, bytes32(0), VAULT, 0);
        vm.expectRevert(RetirementRegistry.ZeroValue.selector);
        reg.retire(BATCH, 1, 10, keccak256("c"), bytes32(0), 0);
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
            uint256 hint = reg.hintFor(BATCH, s);
            vm.prank(operator);
            try reg.retire(BATCH, s, e, c, VAULT, hint) {} catch {}
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
        _assertSortedAndDisjoint(BATCH);
    }

    // --- hints (sorted linked list) -----------------------------------------------------------

    function test_OutOfOrderInsertionKeepsListSorted() public {
        uint256 a = _retire(300, 399);
        uint256 b = _retire(100, 199); // goes before the head
        uint256 c = _retire(200, 299); // between b and a
        uint256[] memory ids = reg.orderedRetirements(BATCH);
        assertEq(ids.length, 3);
        assertEq(ids[0], b);
        assertEq(ids[1], c);
        assertEq(ids[2], a);
        assertEq(reg.retirementOf(BATCH, 250), c);
        assertEq(reg.retirementOf(BATCH, 50), 0);
        assertEq(reg.retirementOf(BATCH, 400), 0);
    }

    function test_RevertWhen_HintIsNotTheImmediatePredecessor() public {
        uint256 first = _retire(100, 199);
        _retire(300, 399);
        _expectHintRevert(400, 499, first, abi.encodeWithSelector(RetirementRegistry.InvalidHint.selector, first));
    }

    function test_RevertWhen_HintLiesAfterTheRange() public {
        uint256 later = _retire(300, 399);
        _expectHintRevert(100, 199, later, abi.encodeWithSelector(RetirementRegistry.InvalidHint.selector, later));
    }

    function test_RevertWhen_HintIsUnknownOrFromAnotherBatch() public {
        vm.prank(operator);
        reg.registerBatch(BATCH_2, PROJECT, FIRST, LAST);
        uint256 other = _retire(BATCH_2, 1, 10);
        _expectHintRevert(100, 199, 99, abi.encodeWithSelector(RetirementRegistry.InvalidHint.selector, 99));
        _expectHintRevert(100, 199, other, abi.encodeWithSelector(RetirementRegistry.InvalidHint.selector, other));
    }

    function test_ZeroHintWithExistingHeadStillDetectsOverlap() public {
        _retire(100, 199);
        _expectHintRevert(150, 250, 0, abi.encodeWithSelector(RetirementRegistry.AlreadyRetired.selector, 1));
    }

    /// Safety does not depend on the hint: arbitrary (even malicious) hints can only cause reverts,
    /// never an overlapping retirement.
    function testFuzz_AnyHintNeverAllowsDoubleRetirement(
        uint64[8] memory starts,
        uint64[8] memory lens,
        uint256[8] memory hints
    ) public {
        for (uint256 i = 0; i < 8; ++i) {
            uint64 s = uint64(bound(starts[i], FIRST, LAST));
            uint64 e = uint64(bound(lens[i], 0, 150)) + s;
            if (e > LAST) e = LAST;
            uint256 hint = bound(hints[i], 0, reg.retirementCount() + 1);
            bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, s, e);
            vm.prank(operator);
            try reg.retire(BATCH, s, e, c, VAULT, hint) {} catch {}
        }
        _assertSortedAndDisjoint(BATCH);
    }

    function test_GasDoesNotGrowWithBatchSize() public {
        vm.prank(operator);
        reg.registerBatch(BATCH_2, PROJECT, 1, 1_000_000);
        uint256 prev;
        uint256 firstGas;
        uint256 lastGas;
        for (uint64 i = 0; i < 400; ++i) {
            bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH_2, i * 10 + 1, i * 10 + 10);
            vm.prank(operator);
            uint256 g = gasleft();
            prev = reg.retire(BATCH_2, i * 10 + 1, i * 10 + 10, c, VAULT, prev);
            uint256 used = g - gasleft();
            if (i == 1) firstGas = used;
            if (i == 399) lastGas = used;
        }
        assertApproxEqAbs(lastGas, firstGas, 1_000, "retire gas is constant in the number of past retirements");
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
        uint256 second = reg.retire(BATCH, 300, 399, copied, VAULT, first);
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

    // --- access control and admin security (threat model D3) ----------------------------------

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
        reg.retire(BATCH, 20, 30, keccak256("c"), VAULT, id);

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

    /// Compromised operator key: the admin revokes it; past records stay, new writes are refused.
    function test_RevokedOperatorCannotRetire() public {
        uint256 id = _retire(1, 10);
        bytes32 operatorRole = reg.OPERATOR_ROLE();
        vm.prank(admin);
        reg.revokeRole(operatorRole, operator);

        bytes32 c = reg.commitmentOf(BUYER, SALT, BATCH, 20, 30);
        vm.prank(operator);
        _expectUnauthorized(operator, operatorRole);
        reg.retire(BATCH, 20, 30, c, VAULT, id);
        assertEq(reg.getRetirement(id).end, 10);
    }

    /// Admin handover needs two transactions and a waiting period; a single stolen or mistaken
    /// transaction cannot transfer control.
    function test_AdminHandoverIsTwoStepWithDelay() public {
        vm.prank(admin);
        reg.beginDefaultAdminTransfer(stranger);
        (, uint48 schedule) = reg.pendingDefaultAdmin();

        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControlDefaultAdminRules.AccessControlEnforcedDefaultAdminDelay.selector, schedule
            )
        );
        reg.acceptDefaultAdminTransfer();

        vm.warp(schedule + 1);
        vm.prank(stranger);
        reg.acceptDefaultAdminTransfer();
        assertEq(reg.defaultAdmin(), stranger);
        assertFalse(reg.hasRole(reg.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_AdminRoleCannotBeGrantedDirectly() public {
        bytes32 adminRole = reg.DEFAULT_ADMIN_ROLE();
        vm.prank(admin);
        vm.expectRevert(IAccessControlDefaultAdminRules.AccessControlEnforcedDefaultAdminRules.selector);
        reg.grantRole(adminRole, stranger);
    }
}
