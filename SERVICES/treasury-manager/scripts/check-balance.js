/**
 * Check Wallet Balance
 *
 * Simple script to check your wallet balance on testnet
 *
 * Usage:
 *   npx hardhat run scripts/check-balance.js --network sepolia
 */

const hre = require("hardhat");

async function main() {
  console.log("\n💰 Checking Wallet Balance...\n");

  const [deployer] = await hre.ethers.getSigners();
  const network = await hre.ethers.provider.getNetwork();

  console.log("📋 Configuration:");
  console.log("   Network:", network.name);
  console.log("   Chain ID:", network.chainId.toString());
  console.log("   Wallet:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  const balanceInEth = hre.ethers.formatEther(balance);

  console.log("\n💵 Balance:", balanceInEth, "ETH");

  if (parseFloat(balanceInEth) < 0.1) {
    console.log("\n⚠️  WARNING: Low balance!");
    console.log("   You need at least 0.2 ETH for deployment and testing");
    console.log("   Get testnet ETH from: https://sepoliafaucet.com/");
  } else {
    console.log("\n✅ Balance sufficient for deployment and testing");
  }

  console.log("\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
