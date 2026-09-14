// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IdentityRegistry
 * @notice On-chain registry of decentralized identities (DIDs) for the SIH 26125
 *         extension. IDENTITY ONLY — it does NOT store or manage roles. Roles are
 *         owned solely by PlatformAccessControl (single role authority).
 *
 * Stores, per didHash (keccak256 of the DID string):
 *   - pubKeyHash  keccak256 of the 65-byte uncompressed secp256k1 public key
 *   - status      0 = none, 1 = active, 2 = revoked
 *   - registeredAt
 *
 * No PII / PHI is ever stored — only hashes. Administrative actions
 * (register/revoke) require ADMIN_ROLE on the PlatformAccessControl contract,
 * so there is a single source of truth for authorization.
 */

interface IPlatformAccessControl {
    function ADMIN_ROLE() external view returns (bytes32);
    function hasRole(bytes32 role, address account) external view returns (bool);
}

contract IdentityRegistry {
    enum Status {
        None,
        Active,
        Revoked
    }

    struct Identity {
        bytes32 pubKeyHash;
        Status status;
        uint256 registeredAt;
    }

    IPlatformAccessControl public immutable accessControl;

    mapping(bytes32 => Identity) private _identities;

    event IdentityRegistered(bytes32 indexed didHash, bytes32 pubKeyHash);
    event IdentityRevoked(bytes32 indexed didHash);

    modifier onlyAdmin() {
        require(
            accessControl.hasRole(accessControl.ADMIN_ROLE(), msg.sender),
            "caller is not ADMIN"
        );
        _;
    }

    constructor(address accessControlAddress) {
        require(accessControlAddress != address(0), "access control required");
        accessControl = IPlatformAccessControl(accessControlAddress);
    }

    /// @notice Register a DID with its public-key hash. ADMIN only.
    function register(bytes32 didHash, bytes32 pubKeyHash) external onlyAdmin {
        require(didHash != bytes32(0), "did required");
        require(_identities[didHash].status == Status.None, "already registered");
        _identities[didHash] = Identity({
            pubKeyHash: pubKeyHash,
            status: Status.Active,
            registeredAt: block.timestamp
        });
        emit IdentityRegistered(didHash, pubKeyHash);
    }

    /// @notice Revoke a DID. ADMIN only. Subsequent isVerified() returns false.
    function revoke(bytes32 didHash) external onlyAdmin {
        require(_identities[didHash].status == Status.Active, "not active");
        _identities[didHash].status = Status.Revoked;
        emit IdentityRevoked(didHash);
    }

    /// @notice True iff the DID is registered and active.
    function isVerified(bytes32 didHash) external view returns (bool) {
        return _identities[didHash].status == Status.Active;
    }

    /// @notice The registered public-key hash for a DID (bytes32(0) if none).
    function pubKeyHashOf(bytes32 didHash) external view returns (bytes32) {
        return _identities[didHash].pubKeyHash;
    }

    /// @notice The numeric status (0 none, 1 active, 2 revoked).
    function statusOf(bytes32 didHash) external view returns (uint8) {
        return uint8(_identities[didHash].status);
    }
}
