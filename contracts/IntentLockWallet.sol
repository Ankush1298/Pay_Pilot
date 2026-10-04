// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Clones} from "@openzeppelin/contracts/proxy/Clones.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {P256} from "@openzeppelin/contracts/utils/cryptography/P256.sol";
import {WebAuthn} from "@openzeppelin/contracts/utils/cryptography/WebAuthn.sol";

/// @title IntentLockWallet
/// @notice A non-ERC-4337 smart account whose owner is one or more P-256/WebAuthn passkeys.
///         The relayer can submit transactions, but cannot move funds without the service
///         policy signature; STEP_UP transactions additionally require a valid WebAuthn assertion.
contract IntentLockWallet {
    using ECDSA for bytes32;

    address public policySigner;
    uint256 public perTxLimit;
    uint256 public dailyLimit;
    uint256 public windowStart;
    uint256 public spentInWindow;
    bool public frozen;
    bool public initialized;

    struct P256PublicKey { uint256 x; uint256 y; bool active; }
    mapping(bytes32 => P256PublicKey) public passkeys;
    bytes32[] public passkeyIds;
    mapping(address => bool) public trustedMerchant;
    mapping(bytes32 => bool) public used;

    struct Intent {
        address merchant;
        uint256 amount;
        bytes32 purposeHash;
        uint64 expiry;
        uint256 nonce;
    }

    event Executed(bytes32 indexed intentHash, address indexed merchant, uint256 amount, bool passkeyApproved);
    event Frozen(address indexed by);
    event PasskeyAdded(bytes32 indexed keyId, uint256 x, uint256 y);
    event PasskeyRemoved(bytes32 indexed keyId);
    event TrustedMerchantSet(address indexed merchant, bool trusted);
    event PolicyChanged(uint256 perTxLimit, uint256 dailyLimit);

    modifier onlyPolicySigner() { require(msg.sender == policySigner, "not policy signer"); _; }

    function initialize(
        bytes32 initialKeyId,
        uint256 pubX,
        uint256 pubY,
        address _policySigner,
        uint256 _perTxLimit,
        uint256 _dailyLimit,
        address[] calldata trustedMerchants
    ) external {
        require(!initialized, "already initialized");
        require(_policySigner != address(0), "bad policy signer");
        require(P256.isValidPublicKey(pubX, pubY), "bad P256 key");
        initialized = true;
        policySigner = _policySigner;
        perTxLimit = _perTxLimit;
        dailyLimit = _dailyLimit;
        windowStart = block.timestamp;
        passkeys[initialKeyId] = P256PublicKey(pubX, pubY, true);
        passkeyIds.push(initialKeyId);
        for (uint256 i = 0; i < trustedMerchants.length; i++) {
            trustedMerchant[trustedMerchants[i]] = true;
            emit TrustedMerchantSet(trustedMerchants[i], true);
        }
        emit PasskeyAdded(initialKeyId, pubX, pubY);
    }

    receive() external payable {}

    function hashIntent(Intent calldata i) public view returns (bytes32) {
        return keccak256(abi.encode(block.chainid, address(this), i.merchant, i.amount, i.purposeHash, i.expiry, i.nonce));
    }

    function execute(
        Intent calldata i,
        bytes calldata policySig,
        bytes32 keyId,
        WebAuthn.WebAuthnAuth calldata auth
    ) external {
        require(!frozen, "frozen");
        require(block.timestamp <= i.expiry, "expired");
        bytes32 h = hashIntent(i);
        require(!used[h], "replay");
        require(_validPolicySignature(h, policySig), "bad policy signature");

        if (block.timestamp >= windowStart + 1 days) {
            windowStart = block.timestamp;
            spentInWindow = 0;
        }

        bool needsPasskey = !trustedMerchant[i.merchant]
            || i.amount > perTxLimit
            || spentInWindow + i.amount > dailyLimit;

        if (needsPasskey) {
            require(passkeys[keyId].active, "passkey not active");
            P256PublicKey memory pk = passkeys[keyId];
            bytes memory challenge = abi.encodePacked(h);
            require(WebAuthn.verify(challenge, auth, bytes32(pk.x), bytes32(pk.y), true), "invalid WebAuthn");
        } else {
            spentInWindow += i.amount;
        }

        used[h] = true;
        (bool ok,) = payable(i.merchant).call{value: i.amount}("");
        require(ok, "payment failed");
        emit Executed(h, i.merchant, i.amount, needsPasskey);
    }

    /// @notice Add a second passkey. In production this should be invoked through a user-authenticated
    /// account operation; this demo exposes it to the policy service only after the service has already
    /// authenticated the new credential server-side.
    function addPasskey(bytes32 keyId, uint256 x, uint256 y) external onlyPolicySigner {
        require(P256.isValidPublicKey(x, y), "bad P256 key");
        passkeys[keyId] = P256PublicKey(x, y, true);
        passkeyIds.push(keyId);
        emit PasskeyAdded(keyId, x, y);
    }

    function removePasskey(bytes32 keyId) external onlyPolicySigner {
        require(passkeyIds.length > 1, "cannot remove last passkey");
        passkeys[keyId].active = false;
        emit PasskeyRemoved(keyId);
    }

    function setTrustedMerchant(address merchant, bool trusted) external onlyPolicySigner {
        trustedMerchant[merchant] = trusted;
        emit TrustedMerchantSet(merchant, trusted);
    }

    function hashPolicy(uint256 newPerTxLimit, uint256 newDailyLimit) public view returns (bytes32) {
        return keccak256(abi.encode(block.chainid, address(this), newPerTxLimit, newDailyLimit, keccak256("IntentLock policy")));
    }

    function setPolicy(
        uint256 newPerTxLimit,
        uint256 newDailyLimit,
        bytes32 intentHash,
        bytes32 keyId,
        WebAuthn.WebAuthnAuth calldata auth,
        bytes calldata policySig
    ) external {
        bytes32 h = hashPolicy(newPerTxLimit, newDailyLimit);
        require(ECDSA.recover(MessageHashUtils.toEthSignedMessageHash(h), policySig) == policySigner, "bad policy signature");
        P256PublicKey memory pk = passkeys[keyId];
        require(pk.active, "passkey not active");
        require(WebAuthn.verify(abi.encodePacked(intentHash), auth, bytes32(pk.x), bytes32(pk.y), true), "invalid WebAuthn");
        perTxLimit = newPerTxLimit;
        dailyLimit = newDailyLimit;
        emit PolicyChanged(newPerTxLimit, newDailyLimit);
    }

    function freeze() external onlyPolicySigner {
        frozen = true;
        emit Frozen(msg.sender);
    }

    function _validPolicySignature(bytes32 h, bytes calldata sig) internal view returns (bool) {
        bytes32 digest = MessageHashUtils.toEthSignedMessageHash(h);
        return ECDSA.recover(digest, sig) == policySigner;
    }
}

contract IntentLockFactory {
    address public immutable implementation;
    event WalletCreated(address indexed wallet, bytes32 indexed keyId);

    constructor() { implementation = address(new IntentLockWallet()); }

    function saltFor(uint256 x, uint256 y) public pure returns (bytes32) {
        return keccak256(abi.encode(x, y));
    }

    function predictAddress(uint256 x, uint256 y) public view returns (address) {
        return Clones.predictDeterministicAddress(implementation, saltFor(x, y), address(this));
    }

    function createWallet(
        bytes32 keyId,
        uint256 x,
        uint256 y,
        address policySigner,
        uint256 perTxLimit,
        uint256 dailyLimit,
        address[] calldata trustedMerchants
    ) external returns (address wallet) {
        bytes32 salt = saltFor(x, y);
        wallet = Clones.predictDeterministicAddress(implementation, salt, address(this));
        if (wallet.code.length == 0) {
            wallet = Clones.cloneDeterministic(implementation, salt);
            IntentLockWallet(payable(wallet)).initialize(keyId, x, y, policySigner, perTxLimit, dailyLimit, trustedMerchants);
            emit WalletCreated(wallet, keyId);
        }
    }
}
