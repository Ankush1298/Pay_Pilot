// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {PayPilotWallet, PayPilotFactory} from "../PayPilotWallet.sol";

contract PayPilotWalletTest is Test {
    PayPilotFactory factory;
    address policy = makeAddr("policy");
    uint256 x = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296;
    uint256 y = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5;

    function setUp() public { factory = new PayPilotFactory(); }

    function testDeterministicAddress() public {
        address predicted = factory.predictAddress(x, y);
        address created = factory.createWallet(bytes32(uint256(1)), x, y, policy, 1500, 5000, new address[](0));
        assertEq(created, predicted);
        assertGt(created.code.length, 0);
    }

    function testSecondCreateReturnsSameWallet() public {
        address a = factory.createWallet(bytes32(uint256(1)), x, y, policy, 1500, 5000, new address[](0));
        address b = factory.createWallet(bytes32(uint256(1)), x, y, policy, 1500, 5000, new address[](0));
        assertEq(a, b);
    }
}
