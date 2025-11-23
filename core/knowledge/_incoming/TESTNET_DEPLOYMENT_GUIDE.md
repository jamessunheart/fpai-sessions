# 🚀 FPAI TOKEN - Testnet Deployment Guide

**Complete step-by-step guide to deploy and test FPAI Token on Sepolia testnet**

---

## 📋 PREREQUISITES

### **1. Install Node.js**
```bash
# Check if installed
node --version
npm --version

# If not installed, download from:
# https://nodejs.org/ (use LTS version)
```

### **2. Create Test Wallet**
```bash
# IMPORTANT: Create a NEW wallet just for testing
# Never use your main wallet with private keys in code!

# Recommended: Use MetaMask
# 1. Install MetaMask browser extension
# 2. Create new wallet
# 3. Switch to Sepolia Testnet
# 4. Copy your wallet address
# 5. Export private key (Settings > Account Details > Export Private Key)
```

### **3. Get Testnet ETH**

You'll need Sepolia ETH for:
- Deploying contract (~0.05 ETH)
- Testing transactions (~0.1 ETH)
- Total needed: **~0.2 ETH**

**Sepolia Faucets:**
- https://sepoliafaucet.com/
- https://faucets.chain.link/sepolia
- https://faucet.quicknode.com/ethereum/sepolia

**Steps:**
1. Go to faucet website
2. Enter your wallet address
3. Complete verification (may require Twitter/GitHub)
4. Wait for ETH to arrive (~1-5 minutes)
5. Check balance in MetaMask

### **4. Get RPC URL**

Free RPC providers:

**Infura (Recommended):**
1. Go to https://infura.io/
2. Sign up (free)
3. Create new project
4. Copy Sepolia endpoint: `https://sepolia.infura.io/v3/YOUR-PROJECT-ID`

**Alchemy:**
1. Go to https://www.alchemy.com/
2. Sign up (free)
3. Create app (select Sepolia)
4. Copy HTTP URL

### **5. Get Etherscan API Key**

For contract verification:
1. Go to https://etherscan.io/
2. Sign up
3. Go to https://etherscan.io/myapikey
4. Create new API key
5. Copy the key

---

## 🛠️ SETUP

### **Step 1: Install Dependencies**

```bash
cd /Users/jamessunheart/Development/SERVICES/treasury-manager

# Install Node packages
npm install

# This installs:
# - Hardhat (deployment framework)
# - OpenZeppelin contracts (security)
# - Ethers.js (blockchain interaction)
```

### **Step 2: Configure Environment**

```bash
# Copy example env file
cp .env.testnet.example .env

# Edit .env with your values
nano .env
# (or use your preferred editor)
```

**Fill in your .env:**
```bash
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR-PROJECT-ID
PRIVATE_KEY=your_private_key_here_without_0x_prefix
TREASURY_MANAGER_ADDRESS=0x0000000000000000000000000000000000000000
ETHERSCAN_API_KEY=your_etherscan_api_key_here
```

**⚠️ SECURITY WARNING:**
- Never commit .env to git
- Never share your private key
- Use a separate wallet for testing
- .gitignore already includes .env

### **Step 3: Verify Setup**

```bash
# Check Hardhat is working
npx hardhat --version
# Should show: 2.19.4 or similar

# Check your wallet balance
npx hardhat run scripts/check-balance.js --network sepolia
```

---

## 🔨 COMPILATION

### **Compile Smart Contracts**

```bash
npx hardhat compile
```

**Expected output:**
```
Compiled 1 Solidity file successfully
```

**What this does:**
- Compiles FPAIToken.sol
- Checks for syntax errors
- Generates ABI (interface definition)
- Creates bytecode for deployment

**Common errors:**
- "OpenZeppelin contracts not found" → Run `npm install`
- "Solidity version mismatch" → Check hardhat.config.js

---

## 🧪 LOCAL TESTING

### **Run Automated Tests**

Before deploying to testnet, run comprehensive tests locally:

```bash
# Run all tests
npx hardhat test

# Run with gas reporting
REPORT_GAS=true npx hardhat test

# Run specific test
npx hardhat test --grep "Token Sale"
```

**Expected output:**
```
  FPAIToken
    Deployment
      ✓ Should set the correct name and symbol
      ✓ Should mint total supply to owner
      ...
    Token Sale
      ✓ Should allow token purchase during sale
      ...
    Profit Distribution
      ✓ Should allow treasury manager to distribute profits
      ...

  68 passing (2s)
```

**What this tests:**
- ✅ Token deployment
- ✅ Token sale functionality
- ✅ Profit distributions
- ✅ Buyback & burn
- ✅ Governance
- ✅ Admin functions
- ✅ Security features

**If tests fail:**
1. Read error message carefully
2. Check contract logic
3. Verify test setup
4. Ask for help if needed

---

## 🚀 TESTNET DEPLOYMENT

### **Step 1: Deploy Contract**

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

**Expected output:**
```
======================================================================
🚀 FPAI TOKEN DEPLOYMENT
======================================================================

📋 Deployment Configuration:
   Network: sepolia (Chain ID: 11155111)
   Deployer: 0x1234...5678
   Balance: 0.5 ETH

📦 Deploying FPAIToken contract...
   Estimating gas...
   Estimated gas: 2500000
   Estimated cost: 0.025 ETH

   Deploying...

✅ FPAIToken deployed successfully!
   Contract Address: 0xABCD...EFGH
   Transaction Hash: 0x1234...
   Gas Used: 2450000
   Block Number: 12345678

📊 Token Information:
   Name: Full Potential AI Token
   Symbol: FPAI
   Total Supply: 100,000,000.0 FPAI
   Decimals: 18
   Owner: 0x1234...5678

💾 Deployment info saved to: deployments/sepolia-1234567890.json

======================================================================
🎯 NEXT STEPS
======================================================================

1. VERIFY CONTRACT ON ETHERSCAN:
   npx hardhat verify --network sepolia 0xABCD...EFGH

2. TRANSFER TOKENS FOR SALE:
   ...

======================================================================
```

**Save this information:**
- ✅ Contract Address
- ✅ Transaction Hash
- ✅ Block Number

### **Step 2: Verify on Etherscan**

```bash
# Replace with your deployed contract address
npx hardhat verify --network sepolia 0xABCD...EFGH
```

**Expected output:**
```
Successfully verified contract FPAIToken on Etherscan.
https://sepolia.etherscan.io/address/0xABCD...EFGH#code
```

**What this does:**
- Uploads source code to Etherscan
- Verifies it matches deployed bytecode
- Enables public code viewing
- Allows direct contract interaction on Etherscan

**View your contract:**
1. Go to the Etherscan URL
2. Click "Contract" tab
3. See verified code ✅
4. Click "Read Contract" - view state
5. Click "Write Contract" - interact with functions

---

## 🧪 TESTING ON TESTNET

### **Method 1: Automated Testing Script**

```bash
# Update contract address in .env
echo "FPAI_CONTRACT_ADDRESS=0xABCD...EFGH" >> .env

# Run comprehensive tests
npx hardhat run scripts/test-functions.js --network sepolia
```

**What this tests:**
1. ✅ Basic token info
2. ✅ Token transfers
3. ✅ Token sale (buy tokens)
4. ✅ Profit distribution & claiming
5. ✅ Buyback & burn
6. ✅ Governance (proposals & voting)
7. ✅ Admin functions (pause/unpause)

**Expected output:**
```
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
🧪 FPAI TOKEN - FUNCTION TESTING
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

======================================================================
TEST 1: BASIC TOKEN INFO
======================================================================
✅ Test 1 passed: Basic info retrieved

======================================================================
TEST 2: TOKEN TRANSFER
======================================================================
✅ Test 2 passed: Transfer successful

...

🎉 ALL TESTS PASSED!
```

### **Method 2: Manual Testing via Etherscan**

1. **Go to your contract on Etherscan**
   - https://sepolia.etherscan.io/address/0xYOUR_ADDRESS

2. **Read Contract (View State):**
   - Click "Contract" tab
   - Click "Read Contract"
   - Try these functions:
     - `name()` → Should return "Full Potential AI Token"
     - `symbol()` → Should return "FPAI"
     - `totalSupply()` → Should return 100000000000000000000000000
     - `balanceOf(your_address)` → Shows your balance
     - `saleActive()` → Is sale active?

3. **Write Contract (Execute Transactions):**
   - Click "Write Contract"
   - Click "Connect to Web3" (connect MetaMask)
   - Try these functions:

**Start Token Sale:**
```
Function: startSale()
Click "Write"
Confirm in MetaMask
Wait for confirmation
```

**Buy Tokens:**
```
Function: buyTokens()
payableAmount: 0.05 (ETH)
Click "Write"
Confirm in MetaMask
Check your FPAI balance increased
```

**Distribute Profits:**
```
Function: distributeProfits(uint256 totalProfit)
totalProfit: 1000000000000000000 (1 ETH in wei)
payableAmount: 1 (must match totalProfit)
Click "Write"
```

**Claim Profits:**
```
Function: claimProfits()
Click "Write"
Receive ETH to your wallet
```

### **Method 3: Test with MetaMask**

**Add FPAI Token to MetaMask:**
1. Open MetaMask
2. Click "Import tokens"
3. Enter contract address: 0xYOUR_ADDRESS
4. Token symbol: FPAI
5. Decimals: 18
6. Click "Add"

**Now you can:**
- See your FPAI balance
- Send FPAI to other addresses
- Track token transfers

---

## 📊 MONITORING

### **View on Sepolia Etherscan**

**Contract Overview:**
- https://sepolia.etherscan.io/address/0xYOUR_ADDRESS

**What you can see:**
- All transactions
- Token transfers
- Balance
- Contract code (after verification)
- Events emitted

**Useful tabs:**
- **Transactions:** All contract interactions
- **Token Transfers:** FPAI movements
- **Events:** Detailed event logs
- **Contract:** Read/write functions

### **Track Key Metrics**

**Token Sale:**
- Total raised: `totalRaised()`
- Tokens sold: Check contract balance
- Number of buyers: Count unique addresses

**Profit Distributions:**
- Total distributed: `totalProfitsDistributed()`
- Current period: `currentDistributionPeriod()`
- Last distribution: `lastDistributionTime()`

**Buyback & Burn:**
- Total burned: `totalBurned()`
- Total buyback: `totalBuybackAmount()`
- Current supply: `totalSupply()`

---

## 🐛 TROUBLESHOOTING

### **Common Issues**

**1. "Insufficient funds" error**
- You need more Sepolia ETH
- Get more from faucets
- Check balance: `npx hardhat run scripts/check-balance.js --network sepolia`

**2. "Nonce too high" error**
- Reset MetaMask nonce
- Settings > Advanced > Reset Account

**3. "Transaction underpriced" error**
- Gas price too low
- Wait and retry
- Or increase gas in hardhat.config.js

**4. "Contract not verified" on Etherscan**
- Run verification again
- Check Etherscan API key
- Make sure contract compiled correctly

**5. "Private key error"**
- Check .env has correct key
- Remove "0x" prefix
- Ensure wallet has ETH

**6. Tests failing locally**
- Run `npm install` again
- Check Hardhat version
- Clear cache: `npx hardhat clean`

---

## ✅ VERIFICATION CHECKLIST

Before moving to mainnet, verify:

**Smart Contract:**
- [ ] All automated tests passing (68 tests)
- [ ] Deployed to Sepolia successfully
- [ ] Verified on Etherscan
- [ ] Contract code publicly viewable

**Token Sale:**
- [ ] Can start/end sale
- [ ] Can buy tokens with ETH
- [ ] Correct token amount received
- [ ] Min/max purchase limits work
- [ ] Total raised tracked correctly

**Profit Distribution:**
- [ ] Treasury manager set
- [ ] Can distribute profits
- [ ] Profit per token calculated correctly
- [ ] Holders can claim profits
- [ ] Claimed amount matches expected

**Buyback & Burn:**
- [ ] Can execute buyback
- [ ] Tokens burned correctly
- [ ] Total supply decreases
- [ ] Total burned tracked

**Governance:**
- [ ] Can create proposals (with 10M+ tokens)
- [ ] Can vote on proposals
- [ ] Voting power = token balance
- [ ] Proposals execute after deadline

**Admin:**
- [ ] Can pause/unpause
- [ ] Transfers blocked when paused
- [ ] Only owner can call admin functions
- [ ] Treasury manager updatable

**Security:**
- [ ] No reentrancy vulnerabilities
- [ ] Pausable works correctly
- [ ] Access control enforced
- [ ] No unauthorized access

---

## 🎯 SUCCESS CRITERIA

**Testnet deployment is successful when:**

✅ Contract deployed to Sepolia
✅ Verified on Etherscan
✅ All 68 automated tests passing
✅ Manual testing via Etherscan works
✅ Token visible in MetaMask
✅ Token sale functions correctly
✅ Profit distribution works
✅ Buyback & burn functional
✅ Governance operational
✅ No security issues found

**When all criteria met → Ready for audit & mainnet!**

---

## 📞 NEXT STEPS AFTER TESTNET

### **1. Smart Contract Audit**
- Get professional audit (CertiK, Trail of Bits, OpenZeppelin)
- Cost: $10-25K
- Timeline: 2-3 weeks
- Fix any findings

### **2. Final Preparation**
- Update deployment scripts for mainnet
- Prepare multi-sig wallet for treasury
- Set up monitoring infrastructure
- Create deployment checklist

### **3. Mainnet Deployment**
- Deploy to Ethereum mainnet
- Verify on Etherscan
- Transfer tokens for sale
- Start marketing campaign
- Launch token sale! 🚀

---

## 💡 TIPS

**Gas Optimization:**
- Deploy during low activity (weekends)
- Check gas prices: https://etherscan.io/gastracker
- Use `gasPrice: "auto"` in config

**Testing Best Practices:**
- Test with multiple accounts
- Test edge cases
- Simulate real-world scenarios
- Document all findings

**Security:**
- Never use mainnet private keys on testnet
- Keep .env file secure
- Use hardware wallet for mainnet
- Implement multi-sig for treasury

---

## 🔗 USEFUL LINKS

**Testnet Resources:**
- Sepolia Etherscan: https://sepolia.etherscan.io/
- Sepolia Faucet: https://sepoliafaucet.com/
- Chainlist (RPC URLs): https://chainlist.org/

**Documentation:**
- Hardhat Docs: https://hardhat.org/docs
- OpenZeppelin: https://docs.openzeppelin.com/
- Ethers.js: https://docs.ethers.org/

**Tools:**
- Gas Tracker: https://etherscan.io/gastracker
- Unit Converter: https://eth-converter.com/
- ABI Decoder: https://abi.hashex.org/

---

## 🚀 READY TO DEPLOY?

**Quick Start Commands:**

```bash
# 1. Setup
npm install
cp .env.testnet.example .env
# Edit .env with your values

# 2. Compile
npx hardhat compile

# 3. Test locally
npx hardhat test

# 4. Deploy to Sepolia
npx hardhat run scripts/deploy.js --network sepolia

# 5. Verify
npx hardhat verify --network sepolia <CONTRACT_ADDRESS>

# 6. Test on testnet
npx hardhat run scripts/test-functions.js --network sepolia
```

**You got this! 🔥**

---

**Questions or issues? Check troubleshooting section or review the code!**
