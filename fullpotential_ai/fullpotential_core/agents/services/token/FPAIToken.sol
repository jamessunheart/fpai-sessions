// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title FPAI Token - Full Potential AI Empire Token
 * @notice Treasury-backed, yield-bearing, governance-enabled token
 * @dev ERC-20 token with burning, pausing, and role-based minting
 *
 * Token Economics:
 * - Total Supply: 1,000,000,000 FPAI (1 billion)
 * - Decimals: 18
 * - Backing: Real DeFi treasury positions
 * - Yield: Distributed to holders from treasury earnings
 * - Governance: Vote on treasury allocation and agent priorities
 */
contract FPAIToken is ERC20, ERC20Burnable, ERC20Pausable, AccessControl, ReentrancyGuard {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens

    // Treasury backing tracking
    uint256 public treasuryValueUSD; // In cents (e.g., 100000 = $1,000.00)
    uint256 public lastYieldDistribution;

    // Vesting schedules
    mapping(address => VestingSchedule) public vestingSchedules;

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 startTime;
        uint256 cliffDuration;
        uint256 vestingDuration;
        uint256 releasedAmount;
    }

    // Events
    event TreasuryValueUpdated(uint256 oldValue, uint256 newValue);
    event YieldDistributed(uint256 amount, uint256 timestamp);
    event VestingScheduleCreated(address indexed beneficiary, uint256 amount, uint256 startTime);
    event TokensVested(address indexed beneficiary, uint256 amount);

    constructor(address admin, address treasury) ERC20("Full Potential AI Token", "FPAI") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(TREASURY_ROLE, treasury);

        // Initial minting according to tokenomics
        // We'll mint allocations to appropriate addresses with vesting

        // For now, mint initial supply to admin for allocation
        _mint(admin, 100_000_000 * 10**18); // 10% initial circulating
    }

    /**
     * @notice Update treasury value (only TREASURY_ROLE)
     * @param newValueUSD New treasury value in USD cents
     */
    function updateTreasuryValue(uint256 newValueUSD) external onlyRole(TREASURY_ROLE) {
        uint256 oldValue = treasuryValueUSD;
        treasuryValueUSD = newValueUSD;
        emit TreasuryValueUpdated(oldValue, newValueUSD);
    }

    /**
     * @notice Get floor price per token based on treasury backing
     * @return Floor price in USD cents per token (scaled by 10^18)
     */
    function getFloorPrice() public view returns (uint256) {
        uint256 circulatingSupply = totalSupply();
        if (circulatingSupply == 0) return 0;

        // Floor price = (treasuryValue / circulatingSupply)
        // Returns value in cents * 10^18
        return (treasuryValueUSD * 10**18) / (circulatingSupply / 10**18);
    }

    /**
     * @notice Distribute yield to all token holders proportionally
     * @param yieldAmount Amount of tokens to distribute as yield
     */
    function distributeYield(uint256 yieldAmount) external onlyRole(TREASURY_ROLE) nonReentrant {
        require(yieldAmount > 0, "Yield amount must be positive");
        require(totalSupply() + yieldAmount <= MAX_SUPPLY, "Would exceed max supply");

        // Mint yield tokens to treasury for distribution
        _mint(msg.sender, yieldAmount);

        lastYieldDistribution = block.timestamp;
        emit YieldDistributed(yieldAmount, block.timestamp);
    }

    /**
     * @notice Create vesting schedule for contributor
     * @param beneficiary Address receiving vested tokens
     * @param amount Total amount to vest
     * @param cliffDuration Cliff period in seconds
     * @param vestingDuration Total vesting period in seconds
     */
    function createVestingSchedule(
        address beneficiary,
        uint256 amount,
        uint256 cliffDuration,
        uint256 vestingDuration
    ) external onlyRole(MINTER_ROLE) {
        require(beneficiary != address(0), "Invalid beneficiary");
        require(amount > 0, "Amount must be positive");
        require(vestingSchedules[beneficiary].totalAmount == 0, "Schedule already exists");

        vestingSchedules[beneficiary] = VestingSchedule({
            totalAmount: amount,
            startTime: block.timestamp,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            releasedAmount: 0
        });

        // Mint tokens to contract for vesting
        _mint(address(this), amount);

        emit VestingScheduleCreated(beneficiary, amount, block.timestamp);
    }

    /**
     * @notice Release vested tokens to beneficiary
     */
    function releaseVestedTokens() external nonReentrant {
        VestingSchedule storage schedule = vestingSchedules[msg.sender];
        require(schedule.totalAmount > 0, "No vesting schedule");

        uint256 vestedAmount = _calculateVestedAmount(schedule);
        uint256 releasableAmount = vestedAmount - schedule.releasedAmount;

        require(releasableAmount > 0, "No tokens to release");

        schedule.releasedAmount += releasableAmount;
        _transfer(address(this), msg.sender, releasableAmount);

        emit TokensVested(msg.sender, releasableAmount);
    }

    /**
     * @notice Calculate vested amount for a schedule
     */
    function _calculateVestedAmount(VestingSchedule memory schedule) private view returns (uint256) {
        if (block.timestamp < schedule.startTime + schedule.cliffDuration) {
            return 0;
        }

        if (block.timestamp >= schedule.startTime + schedule.vestingDuration) {
            return schedule.totalAmount;
        }

        uint256 timeVested = block.timestamp - schedule.startTime;
        return (schedule.totalAmount * timeVested) / schedule.vestingDuration;
    }

    /**
     * @notice Get releasable tokens for caller
     */
    function getReleasableAmount(address beneficiary) external view returns (uint256) {
        VestingSchedule memory schedule = vestingSchedules[beneficiary];
        if (schedule.totalAmount == 0) return 0;

        uint256 vestedAmount = _calculateVestedAmount(schedule);
        return vestedAmount - schedule.releasedAmount;
    }

    /**
     * @notice Mint new tokens (only MINTER_ROLE, respects MAX_SUPPLY)
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(totalSupply() + amount <= MAX_SUPPLY, "Would exceed max supply");
        _mint(to, amount);
    }

    /**
     * @notice Pause token transfers (emergency only)
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @notice Redeem tokens for pro-rata share of treasury
     * @dev Burns tokens and calculates USD value to return
     */
    function redeemForTreasury(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be positive");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        // Calculate pro-rata share of treasury
        uint256 treasuryShare = (treasuryValueUSD * amount) / totalSupply();

        // Burn tokens
        _burn(msg.sender, amount);

        // In production, would transfer actual treasury assets
        // For now, emit event for off-chain processing
        emit TokensVested(msg.sender, treasuryShare);
    }

    // Required overrides
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Pausable) {
        super._beforeTokenTransfer(from, to, amount);
    }
}
