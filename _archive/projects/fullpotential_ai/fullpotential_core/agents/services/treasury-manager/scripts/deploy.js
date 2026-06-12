/**
 * FPAI Token Deployment Script
 *
 * Deploys the FPAIToken contract to the specified network
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network sepolia
 *   npx hardhat run scripts/deploy.js --network mainnet
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("\n" + "=".repeat(70));
  console.log("🚀 FPAI TOKEN DEPLOYMENT");
  console.log("=".repeat(70));

  // Get network info
  const network = await hre.ethers.provider.getNetwork();
  const [deployer] = await hre.ethers.getSigners();

  console.log("\n📋 Deployment Configuration:");
  console.log("   Network:", network.name, `(Chain ID: ${network.chainId})`);
  console.log("   Deployer:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("   Balance:", hre.ethers.formatEther(balance), "ETH");

  // Check if this is mainnet
  if (network.chainId === 1n) {
    console.log("\n⚠️  WARNING: You are deploying to MAINNET!");
    console.log("   Make sure you have:");
    console.log("   ✓ Completed smart contract audit");
    console.log("   ✓ Tested extensively on testnet");
    console.log("   ✓ Legal review completed");
    console.log("   ✓ Sufficient ETH for gas");
    console.log("\n   Press Ctrl+C to cancel, or wait 10 seconds to continue...");
    await new Promise(resolve => setTimeout(resolve, 10000));
  }

  // Deploy FPAIToken
  console.log("\n📦 Deploying FPAIToken contract...");

  const FPAIToken = await hre.ethers.getContractFactory("FPAIToken");

  console.log("   Estimating gas...");
  const deploymentData = FPAIToken.getDeployTransaction();
  const estimatedGas = await hre.ethers.provider.estimateGas({
    data: deploymentData.data
  });
  console.log("   Estimated gas:", estimatedGas.toString());

  const feeData = await hre.ethers.provider.getFeeData();
  const estimatedCost = estimatedGas * feeData.gasPrice;
  console.log("   Estimated cost:", hre.ethers.formatEther(estimatedCost), "ETH");

  console.log("\n   Deploying...");
  const token = await FPAIToken.deploy();
  await token.waitForDeployment();

  const tokenAddress = await token.getAddress();

  console.log("\n✅ FPAIToken deployed successfully!");
  console.log("   Contract Address:", tokenAddress);
  console.log("   Transaction Hash:", token.deploymentTransaction().hash);

  // Get deployment details
  const receipt = await token.deploymentTransaction().wait();
  console.log("   Gas Used:", receipt.gasUsed.toString());
  console.log("   Block Number:", receipt.blockNumber);

  // Verify contract data
  console.log("\n📊 Token Information:");
  const name = await token.name();
  const symbol = await token.symbol();
  const totalSupply = await token.totalSupply();
  const decimals = await token.decimals();

  console.log("   Name:", name);
  console.log("   Symbol:", symbol);
  console.log("   Total Supply:", hre.ethers.formatEther(totalSupply), "FPAI");
  console.log("   Decimals:", decimals.toString());
  console.log("   Owner:", deployer.address);

  // Get allocation constants
  const publicSaleAllocation = await token.PUBLIC_SALE_ALLOCATION();
  console.log("\n💰 Token Allocations:");
  console.log("   Public Sale:", hre.ethers.formatEther(publicSaleAllocation), "FPAI (40%)");
  console.log("   Deployer holds:", hre.ethers.formatEther(totalSupply), "FPAI initially");
  console.log("   (Allocate according to tokenomics before sale)");

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    contractAddress: tokenAddress,
    deployer: deployer.address,
    deploymentHash: token.deploymentTransaction().hash,
    blockNumber: receipt.blockNumber,
    gasUsed: receipt.gasUsed.toString(),
    timestamp: new Date().toISOString(),
    tokenName: name,
    tokenSymbol: symbol,
    totalSupply: totalSupply.toString(),
    decimals: decimals.toString()
  };

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir);
  }

  const filename = `${network.name}-${Date.now()}.json`;
  const filepath = path.join(deploymentsDir, filename);
  fs.writeFileSync(filepath, JSON.stringify(deploymentInfo, null, 2));

  console.log("\n💾 Deployment info saved to:", filepath);

  // Next steps
  console.log("\n" + "=".repeat(70));
  console.log("🎯 NEXT STEPS");
  console.log("=".repeat(70));
  console.log("\n1. VERIFY CONTRACT ON ETHERSCAN:");
  console.log(`   npx hardhat verify --network ${network.name} ${tokenAddress}`);

  console.log("\n2. TRANSFER TOKENS FOR SALE:");
  console.log("   Transfer 40M FPAI to contract for public sale");
  console.log("   Use: token.transfer(tokenAddress, publicSaleAllocation)");

  console.log("\n3. SET TREASURY MANAGER:");
  console.log("   token.setTreasuryManager(treasuryAddress)");

  console.log("\n4. START TOKEN SALE:");
  console.log("   token.startSale()");

  console.log("\n5. TEST ALL FUNCTIONS:");
  console.log(`   npx hardhat run scripts/test-functions.js --network ${network.name}`);

  console.log("\n" + "=".repeat(70));
  console.log("✨ Deployment Complete!");
  console.log("=".repeat(70) + "\n");

  // Return contract for verification
  return {
    token,
    tokenAddress,
    deploymentInfo
  };
}

// Execute deployment
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Deployment failed:");
    console.error(error);
    process.exit(1);
  });
