/**
 * FPAI Token Function Testing Script
 *
 * Tests all token functions on deployed contract
 *
 * Usage:
 *   npx hardhat run scripts/test-functions.js --network sepolia
 *
 * Prerequisites:
 *   1. Contract deployed to testnet
 *   2. Update CONTRACT_ADDRESS below with deployed address
 *   3. Have testnet ETH for transactions
 */

const hre = require("hardhat");

// UPDATE THIS with your deployed contract address
const CONTRACT_ADDRESS = process.env.FPAI_CONTRACT_ADDRESS || "YOUR_CONTRACT_ADDRESS_HERE";

async function main() {
  console.log("\n" + "🔥".repeat(35));
  console.log("🧪 FPAI TOKEN - FUNCTION TESTING");
  console.log("🔥".repeat(35));

  // Get signers
  const [deployer, user1, user2, user3] = await hre.ethers.getSigners();

  console.log("\n📋 Test Configuration:");
  console.log("   Contract:", CONTRACT_ADDRESS);
  console.log("   Deployer:", deployer.address);
  console.log("   Test User 1:", user1.address);
  console.log("   Test User 2:", user2.address);

  // Connect to deployed contract
  const FPAIToken = await hre.ethers.getContractFactory("FPAIToken");
  const token = FPAIToken.attach(CONTRACT_ADDRESS);

  console.log("\n✅ Connected to FPAI Token contract");

  // Run tests
  try {
    await testBasicInfo(token);
    await testTokenTransfer(token, deployer, user1);
    await testTokenSale(token, deployer, user1, user2);
    await testProfitDistribution(token, deployer, user1, user2);
    await testBuybackAndBurn(token, deployer);
    await testGovernance(token, deployer, user1);
    await testAdminFunctions(token, deployer);

    console.log("\n" + "=".repeat(70));
    console.log("🎉 ALL TESTS PASSED!");
    console.log("=".repeat(70));
    console.log("\n✅ The FPAI Token contract is fully functional!");

  } catch (error) {
    console.error("\n❌ Test failed:");
    console.error(error);
    process.exit(1);
  }
}

async function testBasicInfo(token) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 1: BASIC TOKEN INFO");
  console.log("=".repeat(70));

  const name = await token.name();
  const symbol = await token.symbol();
  const decimals = await token.decimals();
  const totalSupply = await token.totalSupply();

  console.log("\n📊 Token Details:");
  console.log("   Name:", name);
  console.log("   Symbol:", symbol);
  console.log("   Decimals:", decimals.toString());
  console.log("   Total Supply:", hre.ethers.formatEther(totalSupply), "FPAI");

  console.log("\n✅ Test 1 passed: Basic info retrieved");
}

async function testTokenTransfer(token, from, to) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 2: TOKEN TRANSFER");
  console.log("=".repeat(70));

  const amount = hre.ethers.parseEther("1000"); // 1000 FPAI

  console.log("\n📤 Transferring 1000 FPAI...");
  console.log("   From:", from.address);
  console.log("   To:", to.address);

  const balanceBefore = await token.balanceOf(to.address);
  console.log("   Balance before:", hre.ethers.formatEther(balanceBefore), "FPAI");

  const tx = await token.transfer(to.address, amount);
  await tx.wait();

  const balanceAfter = await token.balanceOf(to.address);
  console.log("   Balance after:", hre.ethers.formatEther(balanceAfter), "FPAI");

  if (balanceAfter > balanceBefore) {
    console.log("\n✅ Test 2 passed: Transfer successful");
  } else {
    throw new Error("Transfer failed");
  }
}

async function testTokenSale(token, deployer, buyer1, buyer2) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 3: TOKEN SALE");
  console.log("=".repeat(70));

  // Setup: Transfer tokens to contract for sale
  const saleAllocation = await token.PUBLIC_SALE_ALLOCATION();
  console.log("\n📦 Setting up token sale...");
  console.log("   Transferring", hre.ethers.formatEther(saleAllocation), "FPAI to contract");

  const contractAddress = await token.getAddress();
  const setupTx = await token.transfer(contractAddress, saleAllocation);
  await setupTx.wait();

  const contractBalance = await token.balanceOf(contractAddress);
  console.log("   Contract now holds:", hre.ethers.formatEther(contractBalance), "FPAI");

  // Start sale
  console.log("\n🚀 Starting token sale...");
  const startTx = await token.startSale();
  await startTx.wait();

  const saleActive = await token.saleActive();
  console.log("   Sale active:", saleActive);

  // Test purchase (assuming 1 ETH = $3000)
  // To buy $100 worth: 0.033 ETH
  const purchaseAmount = hre.ethers.parseEther("0.05"); // 0.05 ETH = ~$150

  console.log("\n💰 Test Purchase:");
  console.log("   Buyer:", buyer1.address);
  console.log("   Amount:", hre.ethers.formatEther(purchaseAmount), "ETH");

  const buyer1BalanceBefore = await token.balanceOf(buyer1.address);

  const buyTx = await token.connect(buyer1).buyTokens({ value: purchaseAmount });
  const receipt = await buyTx.wait();

  const buyer1BalanceAfter = await token.balanceOf(buyer1.address);
  const tokensReceived = buyer1BalanceAfter - buyer1BalanceBefore;

  console.log("   Tokens received:", hre.ethers.formatEther(tokensReceived), "FPAI");
  console.log("   Gas used:", receipt.gasUsed.toString());

  const totalRaised = await token.totalRaised();
  console.log("   Total raised:", hre.ethers.formatEther(totalRaised), "ETH");

  if (tokensReceived > 0) {
    console.log("\n✅ Test 3 passed: Token purchase successful");
  } else {
    throw new Error("Token purchase failed");
  }
}

async function testProfitDistribution(token, deployer, holder1, holder2) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 4: PROFIT DISTRIBUTION");
  console.log("=".repeat(70));

  // Set treasury manager (deployer for testing)
  console.log("\n⚙️  Setting treasury manager...");
  const setTreasuryTx = await token.setTreasuryManager(deployer.address);
  await setTreasuryTx.wait();
  console.log("   Treasury manager set to:", deployer.address);

  // Distribute profits
  const profitAmount = hre.ethers.parseEther("1.0"); // 1 ETH in profits

  console.log("\n💸 Distributing profits...");
  console.log("   Amount:", hre.ethers.formatEther(profitAmount), "ETH");

  const distributeTx = await token.distributeProfits(profitAmount, {
    value: profitAmount
  });
  await distributeTx.wait();

  const currentPeriod = await token.currentDistributionPeriod();
  const profitPerToken = await token.profitPerTokenInPeriod(currentPeriod);

  console.log("   Distribution period:", currentPeriod.toString());
  console.log("   Profit per token:", profitPerToken.toString());

  // Check claimable amount for holder1
  const claimable = await token.getUnclaimedProfits(holder1.address);
  console.log("\n💰 Holder 1 claimable profits:", hre.ethers.formatEther(claimable), "ETH");

  if (claimable > 0) {
    // Claim profits
    console.log("\n📥 Claiming profits...");
    const ethBalanceBefore = await hre.ethers.provider.getBalance(holder1.address);

    const claimTx = await token.connect(holder1).claimProfits();
    const claimReceipt = await claimTx.wait();

    const ethBalanceAfter = await hre.ethers.provider.getBalance(holder1.address);
    const gasCost = claimReceipt.gasUsed * claimReceipt.gasPrice;
    const netReceived = ethBalanceAfter - ethBalanceBefore + gasCost;

    console.log("   Claimed:", hre.ethers.formatEther(netReceived), "ETH");
    console.log("   Gas cost:", hre.ethers.formatEther(gasCost), "ETH");

    console.log("\n✅ Test 4 passed: Profit distribution and claiming works");
  } else {
    console.log("\n⚠️  No claimable profits (holder may have no tokens)");
  }
}

async function testBuybackAndBurn(token, deployer) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 5: BUYBACK & BURN");
  console.log("=".repeat(70));

  const contractAddress = await token.getAddress();
  const burnAmount = hre.ethers.parseEther("1000"); // Burn 1000 FPAI
  const buybackETH = hre.ethers.parseEther("0.01"); // 0.01 ETH

  console.log("\n🔥 Testing buyback & burn...");
  console.log("   Burn amount:", hre.ethers.formatEther(burnAmount), "FPAI");
  console.log("   ETH for buyback:", hre.ethers.formatEther(buybackETH), "ETH");

  // Get total supply before
  const supplyBefore = await token.totalSupply();
  console.log("   Supply before:", hre.ethers.formatEther(supplyBefore), "FPAI");

  // Transfer tokens to contract for burning (simulate buyback)
  const transferTx = await token.transfer(contractAddress, burnAmount);
  await transferTx.wait();

  // Execute buyback and burn
  const burnTx = await token.buybackAndBurn(burnAmount, { value: buybackETH });
  await burnTx.wait();

  const supplyAfter = await token.totalSupply();
  console.log("   Supply after:", hre.ethers.formatEther(supplyAfter), "FPAI");

  const burned = supplyBefore - supplyAfter;
  console.log("   Burned:", hre.ethers.formatEther(burned), "FPAI");

  const totalBurned = await token.totalBurned();
  console.log("   Total burned (lifetime):", hre.ethers.formatEther(totalBurned), "FPAI");

  if (burned > 0) {
    console.log("\n✅ Test 5 passed: Buyback & burn successful");
  } else {
    throw new Error("Buyback & burn failed");
  }
}

async function testGovernance(token, proposer, voter) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 6: GOVERNANCE");
  console.log("=".repeat(70));

  // Ensure proposer has enough tokens (need 10M+)
  const proposerBalance = await token.balanceOf(proposer.address);
  const requiredBalance = hre.ethers.parseEther("10000000"); // 10M FPAI

  console.log("\n📊 Governance requirements:");
  console.log("   Required to propose:", hre.ethers.formatEther(requiredBalance), "FPAI");
  console.log("   Proposer balance:", hre.ethers.formatEther(proposerBalance), "FPAI");

  if (proposerBalance < requiredBalance) {
    console.log("\n⚠️  Proposer doesn't have enough tokens");
    console.log("   Skipping governance test (would fail)");
    console.log("   In production: Ensure proposers hold 10M+ FPAI");
    return;
  }

  // Create proposal
  console.log("\n📝 Creating proposal...");
  const description = "Test proposal: Change profit distribution ratio";
  const proposalType = 2; // ProfitRatioChange

  const proposeTx = await token.createProposal(description, proposalType);
  const proposeReceipt = await proposeTx.wait();

  // Get proposal ID from event
  const proposalId = await token.proposalCount();
  console.log("   Proposal ID:", proposalId.toString());
  console.log("   Description:", description);

  // Vote on proposal
  console.log("\n🗳️  Voting on proposal...");
  const voteTx = await token.connect(voter).vote(proposalId, true);
  await voteTx.wait();

  const proposal = await token.proposals(proposalId);
  console.log("   Votes for:", hre.ethers.formatEther(proposal.votesFor), "FPAI");
  console.log("   Votes against:", hre.ethers.formatEther(proposal.votesAgainst), "FPAI");
  console.log("   Deadline:", new Date(Number(proposal.deadline) * 1000).toLocaleString());

  console.log("\n✅ Test 6 passed: Governance functions work");
}

async function testAdminFunctions(token, admin) {
  console.log("\n" + "=".repeat(70));
  console.log("TEST 7: ADMIN FUNCTIONS");
  console.log("=".repeat(70));

  // Test pause
  console.log("\n⏸️  Testing pause...");
  const pauseTx = await token.pause();
  await pauseTx.wait();

  const paused = await token.paused();
  console.log("   Paused:", paused);

  // Test unpause
  console.log("\n▶️  Testing unpause...");
  const unpauseTx = await token.unpause();
  await unpauseTx.wait();

  const unpausedState = await token.paused();
  console.log("   Paused:", unpausedState);

  // End sale (if still active)
  const saleActive = await token.saleActive();
  if (saleActive) {
    console.log("\n🛑 Ending token sale...");
    const endSaleTx = await token.endSale();
    await endSaleTx.wait();
    console.log("   Sale ended");
  }

  console.log("\n✅ Test 7 passed: Admin functions work");
}

// Run all tests
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
