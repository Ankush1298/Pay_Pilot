// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {IntentLockFactory} from "../IntentLockWallet.sol";

contract Deploy is Script {
    function run() external returns (IntentLockFactory factory) {
        uint256 deployer = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployer);
        factory = new IntentLockFactory();
        vm.stopBroadcast();
        console2.log("IntentLockFactory", address(factory));
        console2.log("IntentLockWallet implementation", factory.implementation());
    }
}
