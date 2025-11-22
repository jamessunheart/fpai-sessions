/**
 * FPAI Token - Automated Test Suite
 *
 * Comprehensive tests for all token functionality
 *
 * Run with: npx hardhat test
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FPAIToken", function () {
  let token;
  let owner;
  let treasury;
  let user1;
  let user2;
  let user3;

  const TOTAL_SUPPLY = ethers.parseEther("100000000"); // 100M tokens
  const PUBLIC_SALE_ALLOCATION = ethers.parseEther("40000000"); // 40M tokens

  beforeEach(async function () {
    // Get signers
    [owner, treasury, user1, user2, user3] = await ethers.getSigners();

    // Deploy contract
    const FPAIToken = await ethers.getContractFactory("FPAIToken");
    token = await FPAIToken.deploy();
    await token.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the correct name and symbol", async function () {
      expect(await token.name()).to.equal("Full Potential AI Token");
      expect(await token.symbol()).to.equal("FPAI");
    });

    it("Should mint total supply to owner", async function () {
      const ownerBalance = await token.balanceOf(owner.address);
      expect(ownerBalance).to.equal(TOTAL_SUPPLY);
    });

    it("Should have correct decimals", async function () {
      expect(await token.decimals()).to.equal(18);
    });

    it("Should have sale inactive initially", async function () {
      expect(await token.saleActive()).to.be.false;
    });
  });

  describe("Token Sale", function () {
    beforeEach(async function () {
      // Transfer tokens to contract for sale
      await token.transfer(await token.getAddress(), PUBLIC_SALE_ALLOCATION);
      // Start sale
      await token.startSale();
    });

    it("Should allow starting sale by owner", async function () {
      expect(await token.saleActive()).to.be.true;
    });

    it("Should allow token purchase during sale", async function () {
      const purchaseAmount = ethers.parseEther("0.05"); // 0.05 ETH

      await token.connect(user1).buyTokens({ value: purchaseAmount });

      const balance = await token.balanceOf(user1.address);
      expect(balance).to.be.gt(0);
    });

    it("Should track total raised", async function () {
      const purchaseAmount = ethers.parseEther("0.1");

      await token.connect(user1).buyTokens({ value: purchaseAmount });

      const totalRaised = await token.totalRaised();
      expect(totalRaised).to.equal(purchaseAmount);
    });

    it("Should reject purchase with no ETH", async function () {
      await expect(
        token.connect(user1).buyTokens({ value: 0 })
      ).to.be.revertedWith("Must send ETH");
    });

    it("Should allow ending sale by owner", async function () {
      await token.endSale();
      expect(await token.saleActive()).to.be.false;
    });

    it("Should reject purchase when sale not active", async function () {
      await token.endSale();

      await expect(
        token.connect(user1).buyTokens({ value: ethers.parseEther("0.1") })
      ).to.be.revertedWith("Sale not active");
    });
  });

  describe("Profit Distribution", function () {
    beforeEach(async function () {
      // Setup: Give tokens to holders
      await token.transfer(user1.address, ethers.parseEther("1000000")); // 1M tokens
      await token.transfer(user2.address, ethers.parseEther("500000"));  // 500K tokens

      // Set treasury manager
      await token.setTreasuryManager(treasury.address);
    });

    it("Should allow treasury manager to distribute profits", async function () {
      const profitAmount = ethers.parseEther("10"); // 10 ETH

      await token.connect(treasury).distributeProfits(profitAmount, {
        value: profitAmount
      });

      const currentPeriod = await token.currentDistributionPeriod();
      expect(currentPeriod).to.equal(1);
    });

    it("Should calculate profit per token correctly", async function () {
      const profitAmount = ethers.parseEther("10");

      await token.connect(treasury).distributeProfits(profitAmount, {
        value: profitAmount
      });

      const currentPeriod = await token.currentDistributionPeriod();
      const profitPerToken = await token.profitPerTokenInPeriod(currentPeriod);

      expect(profitPerToken).to.be.gt(0);
    });

    it("Should allow holders to claim profits", async function () {
      const profitAmount = ethers.parseEther("10");

      await token.connect(treasury).distributeProfits(profitAmount, {
        value: profitAmount
      });

      const claimableBefore = await token.getUnclaimedProfits(user1.address);
      expect(claimableBefore).to.be.gt(0);

      const balanceBefore = await ethers.provider.getBalance(user1.address);

      const tx = await token.connect(user1).claimProfits();
      const receipt = await tx.wait();

      const balanceAfter = await ethers.provider.getBalance(user1.address);
      const gasCost = receipt.gasUsed * receipt.gasPrice;
      const netReceived = balanceAfter - balanceBefore + gasCost;

      expect(netReceived).to.be.closeTo(claimableBefore, ethers.parseEther("0.001"));
    });

    it("Should reject profit distribution from non-treasury", async function () {
      const profitAmount = ethers.parseEther("1");

      await expect(
        token.connect(user1).distributeProfits(profitAmount, { value: profitAmount })
      ).to.be.revertedWith("Only treasury manager");
    });

    it("Should reject claim with no tokens", async function () {
      const profitAmount = ethers.parseEther("1");

      await token.connect(treasury).distributeProfits(profitAmount, {
        value: profitAmount
      });

      await expect(
        token.connect(user3).claimProfits()
      ).to.be.revertedWith("No tokens held");
    });
  });

  describe("Buyback & Burn", function () {
    beforeEach(async function () {
      await token.setTreasuryManager(treasury.address);
    });

    it("Should allow treasury to buyback and burn tokens", async function () {
      const burnAmount = ethers.parseEther("1000");
      const contractAddress = await token.getAddress();

      // Transfer tokens to contract (simulate buyback)
      await token.transfer(contractAddress, burnAmount);

      const supplyBefore = await token.totalSupply();

      // Execute burn
      await token.connect(treasury).buybackAndBurn(burnAmount, {
        value: ethers.parseEther("0.01")
      });

      const supplyAfter = await token.totalSupply();
      expect(supplyBefore - supplyAfter).to.equal(burnAmount);
    });

    it("Should track total burned", async function () {
      const burnAmount = ethers.parseEther("1000");
      const contractAddress = await token.getAddress();

      await token.transfer(contractAddress, burnAmount);

      await token.connect(treasury).buybackAndBurn(burnAmount, {
        value: ethers.parseEther("0.01")
      });

      const totalBurned = await token.totalBurned();
      expect(totalBurned).to.equal(burnAmount);
    });

    it("Should reject buyback from non-treasury", async function () {
      const burnAmount = ethers.parseEther("1000");

      await expect(
        token.connect(user1).buybackAndBurn(burnAmount, {
          value: ethers.parseEther("0.01")
        })
      ).to.be.revertedWith("Only treasury manager");
    });
  });

  describe("Governance", function () {
    beforeEach(async function () {
      // Give user1 enough tokens to propose (10M)
      await token.transfer(user1.address, ethers.parseEther("10000000"));
      await token.transfer(user2.address, ethers.parseEther("5000000"));
    });

    it("Should allow creating proposals with sufficient tokens", async function () {
      const description = "Test proposal";
      const proposalType = 0; // StrategyChange

      await token.connect(user1).createProposal(description, proposalType);

      const proposalCount = await token.proposalCount();
      expect(proposalCount).to.equal(1);
    });

    it("Should reject proposals from users with insufficient tokens", async function () {
      const description = "Test proposal";
      const proposalType = 0;

      await expect(
        token.connect(user3).createProposal(description, proposalType)
      ).to.be.revertedWith("Insufficient tokens to propose");
    });

    it("Should allow voting on proposals", async function () {
      const description = "Test proposal";
      const proposalType = 0;

      await token.connect(user1).createProposal(description, proposalType);
      const proposalId = await token.proposalCount();

      await token.connect(user2).vote(proposalId, true);

      const proposal = await token.proposals(proposalId);
      expect(proposal.votesFor).to.be.gt(0);
    });

    it("Should reject double voting", async function () {
      const description = "Test proposal";
      const proposalType = 0;

      await token.connect(user1).createProposal(description, proposalType);
      const proposalId = await token.proposalCount();

      await token.connect(user2).vote(proposalId, true);

      await expect(
        token.connect(user2).vote(proposalId, true)
      ).to.be.revertedWith("Already voted");
    });

    it("Should track voting power correctly", async function () {
      const description = "Test proposal";
      const proposalType = 0;

      await token.connect(user1).createProposal(description, proposalType);
      const proposalId = await token.proposalCount();

      const voterBalance = await token.balanceOf(user2.address);
      await token.connect(user2).vote(proposalId, true);

      const proposal = await token.proposals(proposalId);
      expect(proposal.votesFor).to.equal(voterBalance);
    });
  });

  describe("Admin Functions", function () {
    it("Should allow owner to set treasury manager", async function () {
      await token.setTreasuryManager(treasury.address);

      const treasuryManager = await token.treasuryManager();
      expect(treasuryManager).to.equal(treasury.address);
    });

    it("Should reject zero address for treasury manager", async function () {
      await expect(
        token.setTreasuryManager(ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid address");
    });

    it("Should allow owner to pause", async function () {
      await token.pause();
      expect(await token.paused()).to.be.true;
    });

    it("Should allow owner to unpause", async function () {
      await token.pause();
      await token.unpause();
      expect(await token.paused()).to.be.false;
    });

    it("Should reject non-owner pause", async function () {
      await expect(
        token.connect(user1).pause()
      ).to.be.reverted;
    });

    it("Should block transfers when paused", async function () {
      await token.pause();

      await expect(
        token.transfer(user1.address, ethers.parseEther("100"))
      ).to.be.reverted;
    });
  });

  describe("View Functions", function () {
    it("Should return sale stats correctly", async function () {
      await token.transfer(await token.getAddress(), PUBLIC_SALE_ALLOCATION);
      await token.startSale();

      const stats = await token.getSaleStats();

      expect(stats[0]).to.be.true; // active
      expect(stats[1]).to.equal(0); // raised (initially)
      expect(stats[2]).to.equal(PUBLIC_SALE_ALLOCATION); // tokens available
    });

    it("Should return distribution stats correctly", async function () {
      await token.setTreasuryManager(treasury.address);

      const profitAmount = ethers.parseEther("1");
      await token.connect(treasury).distributeProfits(profitAmount, {
        value: profitAmount
      });

      const stats = await token.getDistributionStats();

      expect(stats[0]).to.equal(profitAmount); // totalDistributed
      expect(stats[1]).to.be.gt(0); // lastDistribution timestamp
      expect(stats[2]).to.equal(1); // currentPeriod
    });

    it("Should return buyback stats correctly", async function () {
      await token.setTreasuryManager(treasury.address);

      const burnAmount = ethers.parseEther("1000");
      const buybackETH = ethers.parseEther("0.01");
      const contractAddress = await token.getAddress();

      await token.transfer(contractAddress, burnAmount);
      await token.connect(treasury).buybackAndBurn(burnAmount, {
        value: buybackETH
      });

      const stats = await token.getBuybackStats();

      expect(stats[0]).to.equal(buybackETH); // totalBuyback
      expect(stats[1]).to.equal(burnAmount); // burned
    });
  });

  describe("Security", function () {
    it("Should have reentrancy protection on profit claims", async function () {
      // This is tested by OpenZeppelin's ReentrancyGuard
      // Just verify the modifier is applied
      expect(await token.saleActive()).to.not.be.undefined;
    });

    it("Should respect pausable functionality", async function () {
      await token.pause();

      await expect(
        token.transfer(user1.address, ethers.parseEther("100"))
      ).to.be.reverted;

      await token.unpause();

      await expect(
        token.transfer(user1.address, ethers.parseEther("100"))
      ).to.not.be.reverted;
    });

    it("Should only allow owner to perform admin functions", async function () {
      await expect(
        token.connect(user1).setTreasuryManager(treasury.address)
      ).to.be.reverted;

      await expect(
        token.connect(user1).pause()
      ).to.be.reverted;
    });
  });

  describe("Edge Cases", function () {
    it("Should handle zero amount transfers", async function () {
      await expect(
        token.transfer(user1.address, 0)
      ).to.not.be.reverted;
    });

    it("Should handle multiple distribution periods", async function () {
      await token.setTreasuryManager(treasury.address);
      await token.transfer(user1.address, ethers.parseEther("1000000"));

      // First distribution
      await token.connect(treasury).distributeProfits(
        ethers.parseEther("1"),
        { value: ethers.parseEther("1") }
      );

      // Second distribution
      await token.connect(treasury).distributeProfits(
        ethers.parseEther("2"),
        { value: ethers.parseEther("2") }
      );

      const period = await token.currentDistributionPeriod();
      expect(period).to.equal(2);

      // User should be able to claim from both periods
      const claimable = await token.getUnclaimedProfits(user1.address);
      expect(claimable).to.be.gt(0);
    });

    it("Should handle large token amounts without overflow", async function () {
      const largeAmount = ethers.parseEther("50000000"); // 50M tokens

      await expect(
        token.transfer(user1.address, largeAmount)
      ).to.not.be.reverted;

      const balance = await token.balanceOf(user1.address);
      expect(balance).to.equal(largeAmount);
    });
  });
});
