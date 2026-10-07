// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {PayPilotFactory} from "../PayPilotWallet.sol";

contract Deploy is Script {
    function run() external returns (PayPilotFactory factory) {
        uint256 deployer = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployer);
        factory = new PayPilotFactory();
        vm.stopBroadcast();
        console2.log("PayPilotFactory", address(factory));
        console2.log("PayPilotWallet implementation", factory.implementation());
    }
}
