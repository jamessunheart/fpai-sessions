// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title FPAI Token - Full Potential AI Treasury Token
 * @author Full Potential AI
 * @notice AI-managed treasury backed token with profit sharing
 *
 * Features:
 * - ERC-20 standard token
 * - Quarterly profit distributions to holders
 * - Buyback & burn mechanism (deflationary)
 * - Governance voting rights
 * - Treasury integration
 *
 * Tokenomics:
 * - Total Supply: 100,000,000 FPAI
 * - Public Sale: 40% (40M tokens @ $0.01 = $400K raise)
 * - Team/Dev: 20% (vested 2 years)
 * - Treasury Reserve: 15%
 * - Ecosystem: 15%
 * - Early Supporters: 10% (vested 1 year)
 */
contract FPAIToken is ERC20, Ownable, Pausable, ReentrancyGuard {

    // ========================================================================
    // STATE VARIABLES
    // ========================================================================

    /// @notice Total supply: 100 million tokens
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 10**18;

    /// @notice Public sale allocation (40%)
    uint256 public constant PUBLIC_SALE_ALLOCATION = 40_000_000 * 10**18;

    /// @notice Token sale price: $0.01 per FPAI (assuming 18 decimals)
    uint256 public constant TOKEN_PRICE_USD = 10**16; // $0.01 in wei-like units

    /// @notice Minimum purchase: $100 worth
    uint256 public constant MIN_PURCHASE_USD = 100 * 10**18;

    /// @notice Maximum purchase: $25,000 worth (prevents whales)
    uint256 public constant MAX_PURCHASE_USD = 25_000 * 10**18;

    /// @notice Treasury contract address (receives funds, manages DeFi)
    address public treasuryManager;

    /// @notice Total ETH raised from token sale
    uint256 public totalRaised;

    /// @notice Token sale active flag
    bool public saleActive;

    /// @notice Profit distribution tracking
    uint256 public totalProfitsDistributed;
    uint256 public lastDistributionTime;
    uint256 public currentDistributionPeriod;

    /// @notice Holder profit claims
    mapping(address => uint256) public lastClaimPeriod;
    mapping(uint256 => uint256) public profitPerTokenInPeriod;

    /// @notice Buyback tracking
    uint256 public totalBuybackAmount;
    uint256 public totalBurned;

    /// @notice Governance
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => mapping(address => uint256)) public votes;

    struct Proposal {
        string description;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 deadline;
        bool executed;
        ProposalType proposalType;
    }

    enum ProposalType {
        StrategyChange,
        ProtocolAddition,
        ProfitRatioChange,
        EmergencyAction
    }

    // ========================================================================
    // EVENTS
    // ========================================================================

    event TokensPurchased(address indexed buyer, uint256 amount, uint256 ethPaid);
    event ProfitDistributed(uint256 period, uint256 totalAmount, uint256 perToken);
    event ProfitClaimed(address indexed holder, uint256 amount);
    event TokensBuybackAndBurned(uint256 amount, uint256 ethSpent);
    event ProposalCreated(uint256 indexed proposalId, string description);
    event VoteCast(uint256 indexed proposalId, address indexed voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed proposalId);
    event TreasuryManagerUpdated(address indexed newManager);

    // ========================================================================
    // CONSTRUCTOR
    // ========================================================================

    constructor() ERC20("Full Potential AI Token", "FPAI") Ownable(msg.sender) {
        // Mint total supply to deployer initially
        // Will be distributed according to tokenomics
        _mint(msg.sender, TOTAL_SUPPLY);

        saleActive = false;
        lastDistributionTime = block.timestamp;
        currentDistributionPeriod = 0;
    }

    // ========================================================================
    // TOKEN SALE FUNCTIONS
    // ========================================================================

    /**
     * @notice Start the token sale
     * @dev Only owner can activate
     */
    function startSale() external onlyOwner {
        require(!saleActive, "Sale already active");
        saleActive = true;
    }

    /**
     * @notice End the token sale
     * @dev Only owner can deactivate
     */
    function endSale() external onlyOwner {
        require(saleActive, "Sale not active");
        saleActive = false;
    }

    /**
     * @notice Purchase FPAI tokens during public sale
     * @dev Payable function - send ETH to buy tokens
     *
     * Requirements:
     * - Sale must be active
     * - Purchase amount within min/max limits
     * - Sufficient tokens available
     */
    function buyTokens() external payable nonReentrant whenNotPaused {
        require(saleActive, "Sale not active");
        require(msg.value > 0, "Must send ETH");

        // Calculate token amount (simplified - assumes 1 ETH = $3000)
        // In production, use Chainlink oracle for accurate pricing
        uint256 ethPriceUSD = 3000 * 10**18; // $3000 per ETH
        uint256 purchaseUSD = (msg.value * ethPriceUSD) / 10**18;

        require(purchaseUSD >= MIN_PURCHASE_USD, "Below minimum purchase");
        require(purchaseUSD <= MAX_PURCHASE_USD, "Above maximum purchase");

        // Calculate token amount: (purchase USD / token price) = tokens
        uint256 tokenAmount = (purchaseUSD * 10**18) / TOKEN_PRICE_USD;

        require(balanceOf(address(this)) >= tokenAmount, "Insufficient tokens available");

        // Transfer tokens to buyer
        _transfer(address(this), msg.sender, tokenAmount);

        // Track total raised
        totalRaised += msg.value;

        emit TokensPurchased(msg.sender, tokenAmount, msg.value);
    }

    /**
     * @notice Withdraw raised ETH to treasury manager
     * @dev Only owner, after sale ends
     */
    function withdrawRaisedFunds() external onlyOwner nonReentrant {
        require(!saleActive, "Sale still active");
        require(treasuryManager != address(0), "Treasury manager not set");
        require(address(this).balance > 0, "No funds to withdraw");

        uint256 amount = address(this).balance;
        (bool success, ) = treasuryManager.call{value: amount}("");
        require(success, "Transfer failed");
    }

    // ========================================================================
    // PROFIT DISTRIBUTION FUNCTIONS
    // ========================================================================

    /**
     * @notice Distribute treasury profits to token holders
     * @param totalProfit Total profit amount to distribute (in wei)
     * @dev Called by treasury manager quarterly
     *
     * Distribution:
     * - Profit is distributed proportionally to all holders
     * - Holders can claim their share anytime
     * - Unclaimed profits accumulate
     */
    function distributeProfits(uint256 totalProfit) external payable nonReentrant {
        require(msg.sender == treasuryManager, "Only treasury manager");
        require(msg.value == totalProfit, "ETH must match profit amount");
        require(totalProfit > 0, "No profit to distribute");

        // Start new distribution period
        currentDistributionPeriod++;

        // Calculate profit per token
        // Total circulating supply (excluding burned)
        uint256 circulatingSupply = totalSupply();
        require(circulatingSupply > 0, "No circulating supply");

        uint256 profitPerToken = (totalProfit * 10**18) / circulatingSupply;
        profitPerTokenInPeriod[currentDistributionPeriod] = profitPerToken;

        totalProfitsDistributed += totalProfit;
        lastDistributionTime = block.timestamp;

        emit ProfitDistributed(currentDistributionPeriod, totalProfit, profitPerToken);
    }

    /**
     * @notice Claim accumulated profits
     * @dev Holders can claim profits from all unclaimed periods
     */
    function claimProfits() external nonReentrant {
        uint256 holderBalance = balanceOf(msg.sender);
        require(holderBalance > 0, "No tokens held");

        uint256 totalClaimable = 0;

        // Calculate claimable from all unclaimed periods
        for (uint256 period = lastClaimPeriod[msg.sender] + 1; period <= currentDistributionPeriod; period++) {
            uint256 profitPerToken = profitPerTokenInPeriod[period];
            uint256 claimableInPeriod = (holderBalance * profitPerToken) / 10**18;
            totalClaimable += claimableInPeriod;
        }

        require(totalClaimable > 0, "No profits to claim");
        require(address(this).balance >= totalClaimable, "Insufficient contract balance");

        // Update last claim period
        lastClaimPeriod[msg.sender] = currentDistributionPeriod;

        // Transfer profits to holder
        (bool success, ) = msg.sender.call{value: totalClaimable}("");
        require(success, "Transfer failed");

        emit ProfitClaimed(msg.sender, totalClaimable);
    }

    /**
     * @notice View unclaimed profits for an address
     * @param holder Address to check
     * @return Total unclaimed profit amount
     */
    function getUnclaimedProfits(address holder) external view returns (uint256) {
        uint256 holderBalance = balanceOf(holder);
        if (holderBalance == 0) return 0;

        uint256 totalClaimable = 0;

        for (uint256 period = lastClaimPeriod[holder] + 1; period <= currentDistributionPeriod; period++) {
            uint256 profitPerToken = profitPerTokenInPeriod[period];
            uint256 claimableInPeriod = (holderBalance * profitPerToken) / 10**18;
            totalClaimable += claimableInPeriod;
        }

        return totalClaimable;
    }

    // ========================================================================
    // BUYBACK & BURN FUNCTIONS
    // ========================================================================

    /**
     * @notice Buyback FPAI tokens from market and burn them
     * @param amountToBurn Number of tokens to burn
     * @dev Called by treasury manager with ETH for buyback
     *
     * Process:
     * 1. Treasury sends ETH to this contract
     * 2. Contract buys FPAI from DEX (Uniswap)
     * 3. Bought tokens are burned (destroyed)
     * 4. Total supply decreases (deflationary)
     */
    function buybackAndBurn(uint256 amountToBurn) external payable nonReentrant {
        require(msg.sender == treasuryManager, "Only treasury manager");
        require(amountToBurn > 0, "Amount must be > 0");

        // In production, integrate with Uniswap Router to buy tokens
        // For now, simplified: assumes tokens already in contract
        require(balanceOf(address(this)) >= amountToBurn, "Insufficient tokens for burn");

        // Burn tokens (permanently destroy)
        _burn(address(this), amountToBurn);

        totalBuybackAmount += msg.value;
        totalBurned += amountToBurn;

        emit TokensBuybackAndBurned(amountToBurn, msg.value);
    }

    // ========================================================================
    // GOVERNANCE FUNCTIONS
    // ========================================================================

    /**
     * @notice Create a governance proposal
     * @param description Proposal description
     * @param proposalType Type of proposal
     * @dev Requires 10M+ tokens to create proposal (10% of supply)
     */
    function createProposal(
        string memory description,
        ProposalType proposalType
    ) external returns (uint256) {
        require(balanceOf(msg.sender) >= 10_000_000 * 10**18, "Insufficient tokens to propose");

        proposalCount++;
        uint256 proposalId = proposalCount;

        proposals[proposalId] = Proposal({
            description: description,
            votesFor: 0,
            votesAgainst: 0,
            deadline: block.timestamp + 7 days, // 7-day voting period
            executed: false,
            proposalType: proposalType
        });

        emit ProposalCreated(proposalId, description);

        return proposalId;
    }

    /**
     * @notice Vote on a proposal
     * @param proposalId Proposal to vote on
     * @param support True for yes, false for no
     * @dev Voting power = token balance
     */
    function vote(uint256 proposalId, bool support) external {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal");
        Proposal storage proposal = proposals[proposalId];

        require(block.timestamp < proposal.deadline, "Voting ended");
        require(!hasVoted[proposalId][msg.sender], "Already voted");

        uint256 voterBalance = balanceOf(msg.sender);
        require(voterBalance > 0, "No voting power");

        hasVoted[proposalId][msg.sender] = true;
        votes[proposalId][msg.sender] = voterBalance;

        if (support) {
            proposal.votesFor += voterBalance;
        } else {
            proposal.votesAgainst += voterBalance;
        }

        emit VoteCast(proposalId, msg.sender, support, voterBalance);
    }

    /**
     * @notice Execute a passed proposal
     * @param proposalId Proposal to execute
     * @dev Can only execute if passed (>50% of voting tokens voted yes)
     */
    function executeProposal(uint256 proposalId) external {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal");
        Proposal storage proposal = proposals[proposalId];

        require(block.timestamp >= proposal.deadline, "Voting not ended");
        require(!proposal.executed, "Already executed");
        require(proposal.votesFor > proposal.votesAgainst, "Proposal rejected");

        proposal.executed = true;

        // Execution logic would go here
        // For now, just mark as executed

        emit ProposalExecuted(proposalId);
    }

    // ========================================================================
    // ADMIN FUNCTIONS
    // ========================================================================

    /**
     * @notice Set treasury manager address
     * @param _treasuryManager Address of treasury manager contract
     */
    function setTreasuryManager(address _treasuryManager) external onlyOwner {
        require(_treasuryManager != address(0), "Invalid address");
        treasuryManager = _treasuryManager;
        emit TreasuryManagerUpdated(_treasuryManager);
    }

    /**
     * @notice Pause token transfers (emergency only)
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Override update to add pause functionality
     */
    function _update(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._update(from, to, amount);
    }

    // ========================================================================
    // VIEW FUNCTIONS
    // ========================================================================

    /**
     * @notice Get token sale statistics
     */
    function getSaleStats() external view returns (
        bool active,
        uint256 raised,
        uint256 tokensAvailable
    ) {
        return (
            saleActive,
            totalRaised,
            balanceOf(address(this))
        );
    }

    /**
     * @notice Get distribution statistics
     */
    function getDistributionStats() external view returns (
        uint256 totalDistributed,
        uint256 lastDistribution,
        uint256 currentPeriod
    ) {
        return (
            totalProfitsDistributed,
            lastDistributionTime,
            currentDistributionPeriod
        );
    }

    /**
     * @notice Get buyback statistics
     */
    function getBuybackStats() external view returns (
        uint256 totalBuyback,
        uint256 burned
    ) {
        return (
            totalBuybackAmount,
            totalBurned
        );
    }

    // ========================================================================
    // RECEIVE ETHER
    // ========================================================================

    /**
     * @notice Allow contract to receive ETH
     */
    receive() external payable {}
}
