// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IPool {
    function reserve0() external view returns (uint256);
    function reserve1() external view returns (uint256);
}

// Synthetic pipeline fixture, NOT a dataset ground-truth example.
contract Oracle {
    IPool public pool;

    constructor(IPool pool_) { pool = pool_; }

    function borrow(uint256 collateral) external view returns (uint256) {
        uint256 reserve0 = pool.reserve0();
        uint256 reserve1 = pool.reserve1();
        uint256 price = reserve1 * 1e18 / reserve0;
        uint256 valuation = collateral * price / 1e18;
        uint256 amount = valuation / 2;
        require(amount > 0, "zero amount");
        return amount;
    }
}
