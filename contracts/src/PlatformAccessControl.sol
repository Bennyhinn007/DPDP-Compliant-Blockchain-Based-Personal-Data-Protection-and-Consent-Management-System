// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControlEnumerable} from "@openzeppelin/contracts/access/extensions/AccessControlEnumerable.sol";

/**
 * @title PlatformAccessControl
 * @notice SINGLE authoritative on-chain role authority for the SIH 26125
 *         identity/asset extension. Roles: ADMIN, MANAGER, AUDITOR, USER.
 *
 * Additive to the DPDP healthcare platform — this contract governs only the
 * blockchain identity/asset layer and does NOT affect existing backend RBAC or
 * any healthcare functionality.
 *
 * Roles are keyed by `didHash` (keccak256 of the DID string, per the Canonical
 * Derivation spec) rather than by wallet address, so the platform's backend
 * admin key can administer roles on behalf of DID identities while the DID
 * remains the subject of the role. Grants/revokes emit events that form part of
 * the on-chain audit trail.
 */
contract PlatformAccessControl is AccessControlEnumerable {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");
    bytes32 public constant USER_ROLE = keccak256("USER_ROLE");

    /// @notice SIH roles assigned to a DID (a DID may hold multiple roles).
    mapping(bytes32 => mapping(bytes32 => bool)) private _didRoles;

    event SIHRoleGranted(bytes32 indexed didHash, bytes32 indexed role, address indexed by);
    event SIHRoleRevoked(bytes32 indexed didHash, bytes32 indexed role, address indexed by);

    /**
     * @param admin The platform admin address (backend deployer key). Receives
     *              DEFAULT_ADMIN_ROLE and ADMIN_ROLE so it can administer the layer.
     */
    constructor(address admin) {
        require(admin != address(0), "admin required");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
    }

    /// @notice Grant a SIH role to a DID. Caller must hold ADMIN_ROLE.
    function grantSIHRole(bytes32 didHash, bytes32 role) external onlyRole(ADMIN_ROLE) {
        require(_isKnownRole(role), "unknown role");
        require(didHash != bytes32(0), "did required");
        _didRoles[didHash][role] = true;
        emit SIHRoleGranted(didHash, role, msg.sender);
    }

    /// @notice Revoke a SIH role from a DID. Caller must hold ADMIN_ROLE.
    function revokeSIHRole(bytes32 didHash, bytes32 role) external onlyRole(ADMIN_ROLE) {
        require(_isKnownRole(role), "unknown role");
        _didRoles[didHash][role] = false;
        emit SIHRoleRevoked(didHash, role, msg.sender);
    }

    /// @notice True if a DID currently holds the given SIH role.
    function didHasRole(bytes32 didHash, bytes32 role) external view returns (bool) {
        return _didRoles[didHash][role];
    }

    function _isKnownRole(bytes32 role) internal pure returns (bool) {
        return role == ADMIN_ROLE || role == MANAGER_ROLE || role == AUDITOR_ROLE || role == USER_ROLE;
    }
}
