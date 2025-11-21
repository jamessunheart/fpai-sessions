#!/bin/bash
# Create deployment package for hired VAs

echo "=========================================="
echo "📦 CREATING VA DEPLOYMENT PACKAGE"
echo "=========================================="
echo ""

PACKAGE_DIR="/tmp/fpai-testnet-deployment"
PACKAGE_ZIP="/tmp/fpai-testnet-deployment.zip"

# Clean previous package
rm -rf "$PACKAGE_DIR"
rm -f "$PACKAGE_ZIP"

# Create package directory
mkdir -p "$PACKAGE_DIR"

echo "📋 Copying files..."

# Copy essential files
cp TESTNET_DEPLOYMENT_GUIDE.md "$PACKAGE_DIR/"
cp package.json "$PACKAGE_DIR/"
cp hardhat.config.js "$PACKAGE_DIR/"
cp -r contracts "$PACKAGE_DIR/"
cp -r scripts "$PACKAGE_DIR/"
cp -r test "$PACKAGE_DIR/"

# Create .env.example
cat > "$PACKAGE_DIR/.env.example" << 'EOF'
# Ethereum Sepolia Testnet Configuration
# ========================================

# STEP 1: Get Sepolia RPC URL from Infura
# 1. Sign up at https://infura.io (free)
# 2. Create new project
# 3. Copy Sepolia RPC URL
# 4. Paste below (replace YOUR-PROJECT-ID)
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR-PROJECT-ID

# STEP 2: Get your wallet private key
# 1. Open MetaMask
# 2. Click three dots > Account Details > Export Private Key
# 3. Enter password
# 4. Copy private key
# 5. Paste below (NEVER share this!)
# NOTE: Create a NEW wallet for testnet - never use your real wallet!
PRIVATE_KEY=your_private_key_here

# STEP 3: Get Etherscan API key
# 1. Sign up at https://etherscan.io (free)
# 2. Go to API Keys
# 3. Create new API key
# 4. Copy and paste below
ETHERSCAN_API_KEY=your_etherscan_api_key_here

# IMPORTANT SECURITY NOTES:
# - Never commit this file to git
# - Never share your private key
# - Use testnet wallet only (not your real wallet)
# - Store completed credentials in secure vault when done
EOF

# Create README for VAs
cat > "$PACKAGE_DIR/README_FOR_VA.md" << 'EOF'
# 🚀 FPAI Token Testnet Deployment - VA Instructions

**Welcome!** You've been hired to deploy the FPAI token to Ethereum Sepolia testnet.

---

## 📋 QUICK START (10 minutes to understand, 3-4 hours to complete)

### What You'll Do:
1. Setup MetaMask wallet (testnet only)
2. Get free Sepolia ETH from faucet
3. Sign up for Infura (free RPC)
4. Sign up for Etherscan (free verification)
5. Configure `.env` file with your credentials
6. Run deployment commands
7. Verify contract on Etherscan
8. Test token functions
9. Document results and submit

### Payment:
- **$15 fixed** when all deliverables submitted
- **+$5 bonus** if completed in <4 hours with excellent documentation

---

## 📖 COMPLETE GUIDE

**Read this first:** `TESTNET_DEPLOYMENT_GUIDE.md` (40+ pages)

This guide has:
- Step-by-step instructions
- Screenshots for every step
- Troubleshooting section
- FAQ
- Example outputs

---

## 🔧 SETUP

### 1. Install Node.js (if not installed)
```bash
# Check if installed:
node --version
npm --version

# If not installed, download from:
# https://nodejs.org (use LTS version)
```

### 2. Install Dependencies
```bash
# In this directory:
npm install
```

This will install:
- Hardhat (Ethereum development environment)
- OpenZeppelin contracts (security libraries)
- All required tools

### 3. Configure Environment
```bash
# Copy example file:
cp .env.example .env

# Edit .env file and add your credentials:
# - SEPOLIA_RPC_URL (from Infura)
# - PRIVATE_KEY (from MetaMask)
# - ETHERSCAN_API_KEY (from Etherscan)
```

**IMPORTANT:** See `TESTNET_DEPLOYMENT_GUIDE.md` Section 2 for detailed instructions on getting these credentials.

---

## 🚀 DEPLOYMENT

### 1. Compile Contract
```bash
npx hardhat compile
```

Expected output: `Compiled 1 Solidity file successfully`

### 2. Run Tests (Optional but Recommended)
```bash
npx hardhat test
```

Expected output: `38 passing (1s)`

### 3. Deploy to Sepolia
```bash
npx hardhat run scripts/deploy.js --network sepolia
```

Expected output:
```
Deploying FPAI Token to Sepolia...
Contract deployed to: 0xABCD...EFGH
Deployment saved to: deployments/sepolia-deployment.json
```

### 4. Verify on Etherscan
```bash
npx hardhat verify --network sepolia CONTRACT_ADDRESS
```

Replace `CONTRACT_ADDRESS` with your deployed address.

Expected output: `Successfully verified contract`

---

## ✅ DELIVERABLES

**You must provide:**

1. **Contract Address**
   - Example: `0x1234567890abcdef1234567890abcdef12345678`

2. **Etherscan Verification Link**
   - Example: `https://sepolia.etherscan.io/address/0x1234...#code`

3. **Test Screenshots**
   - Screenshot of successful deployment
   - Screenshot of verified contract on Etherscan
   - Screenshot of test transaction

4. **Credentials (stored in secure vault)**
   - MetaMask wallet address
   - Infura project ID
   - Etherscan API key
   - (NOT your private key - we don't need that!)

5. **Completion Report**
   - What worked well?
   - What was confusing?
   - Time breakdown by step
   - Any suggestions for improving the guide?

---

## 🆘 GETTING HELP

### Slack Support
- Join Slack workspace (invite sent separately)
- Ask questions in #testnet-deployment channel
- Response time: <30 minutes during your task

### Common Issues

**"insufficient funds for gas"**
- Solution: Get more Sepolia ETH from faucet (see guide Section 2.3)

**"cannot find module"**
- Solution: Run `npm install` again

**"invalid api key"**
- Solution: Check your `.env` file has correct credentials

**See full troubleshooting guide in `TESTNET_DEPLOYMENT_GUIDE.md` Section 8**

---

## ⏱️ TIME ESTIMATE

| Step | Estimated Time |
|------|----------------|
| Setup (MetaMask, Infura, Etherscan) | 45 min |
| Install dependencies | 10 min |
| Configure .env | 5 min |
| Deploy contract | 30 min |
| Verify on Etherscan | 15 min |
| Test functions | 60 min |
| Document & submit | 30 min |
| **TOTAL** | **3-4 hours** |

Faster completion = bonus! 🎉

---

## 🎯 SUCCESS CRITERIA

**To get paid:**
- ✅ All 5 deliverables submitted
- ✅ Contract deployed to Sepolia (not mainnet!)
- ✅ Contract verified on Etherscan
- ✅ Test transactions successful
- ✅ Completion report submitted

**To get bonus:**
- ✅ All above criteria met
- ✅ Completed in <4 hours
- ✅ Excellent documentation
- ✅ Clear screenshots
- ✅ Helpful feedback on guide

---

## 📞 SUBMISSION

**Submit your deliverables via:**
1. Slack message in #testnet-deployment
2. Or email to [hiring manager email]

**Include:**
- Contract address
- Etherscan link
- Screenshots (upload to Slack or share via Dropbox/Google Drive)
- Credentials (we'll add to secure vault)
- Completion report

**Payment released within 1 hour of verification!**

---

## 🚀 AFTER THIS TASK

**If you do well:**
- Mainnet deployment: $50
- Marketing automation: $75
- API integration: $40-100
- Ongoing work: $8-15/hr (10-20 hrs/week)

**Top performers:**
- Consistent 20+ hours/week
- Rate increases to $15-25/hr
- Team lead opportunities
- Long-term growth path

---

## ⚠️ IMPORTANT REMINDERS

**Security:**
- ✅ Create NEW wallet for testnet only
- ✅ Never use your real wallet
- ✅ Never share private key with anyone
- ✅ Keep .env file secure (don't commit to git)

**This is TESTNET:**
- ✅ Free test cryptocurrency (no real value)
- ✅ Safe learning environment
- ✅ Mistakes are OK!
- ✅ Ask questions if stuck

**Communication:**
- ✅ Update every 1-2 hours on progress
- ✅ Ask immediately if stuck
- ✅ Document as you go (easier than at end)

---

## 🎉 LET'S GET STARTED!

1. Read `TESTNET_DEPLOYMENT_GUIDE.md` (focus on Sections 1-3)
2. Setup MetaMask wallet
3. Get free Sepolia ETH
4. Run deployment commands
5. Submit deliverables
6. Get paid!

**You got this!** 🚀

Questions? Message on Slack anytime.

Good luck!
Full Potential AI Team
EOF

# Create manifest
cat > "$PACKAGE_DIR/MANIFEST.txt" << 'EOF'
FPAI TESTNET DEPLOYMENT PACKAGE
================================

Files included:

📖 Documentation:
  - README_FOR_VA.md (START HERE!)
  - TESTNET_DEPLOYMENT_GUIDE.md (Complete 40+ page guide)

⚙️ Configuration:
  - package.json (Node.js dependencies)
  - hardhat.config.js (Hardhat configuration)
  - .env.example (Template for credentials)

📜 Smart Contract:
  - contracts/FPAIToken.sol (ERC-20 token contract)

🔧 Scripts:
  - scripts/deploy.js (Deployment script)
  - scripts/verify.js (Etherscan verification)
  - scripts/check-balance.js (Check wallet balance)

🧪 Tests:
  - test/FPAIToken.test.js (38 comprehensive tests)

TOTAL SIZE: ~2MB

Quick start:
1. Read README_FOR_VA.md
2. npm install
3. Copy .env.example to .env
4. Fill in credentials
5. npx hardhat run scripts/deploy.js --network sepolia

Support: Slack #testnet-deployment channel
EOF

echo "✅ Files copied"
echo ""
echo "📦 Creating ZIP package..."

# Create ZIP
cd /tmp
zip -r fpai-testnet-deployment.zip fpai-testnet-deployment/ > /dev/null 2>&1

echo "✅ Package created!"
echo ""
echo "=========================================="
echo "📦 PACKAGE READY"
echo "=========================================="
echo ""
echo "Location: $PACKAGE_ZIP"
echo "Size: $(du -h $PACKAGE_ZIP | cut -f1)"
echo ""
echo "Contents:"
echo "  📖 README_FOR_VA.md (start here)"
echo "  📖 TESTNET_DEPLOYMENT_GUIDE.md (complete guide)"
echo "  ⚙️  package.json, hardhat.config.js"
echo "  📜 contracts/FPAIToken.sol"
echo "  🔧 scripts/ (deployment, verification)"
echo "  🧪 test/ (38 tests)"
echo "  📝 .env.example"
echo "  📋 MANIFEST.txt"
echo ""
echo "=========================================="
echo "📤 HOW TO SEND TO VAs"
echo "=========================================="
echo ""
echo "Option 1: Email"
echo "  - Attach $PACKAGE_ZIP to email"
echo "  - Include Slack workspace invite"
echo ""
echo "Option 2: File sharing"
echo "  - Upload to Dropbox/Google Drive"
echo "  - Share link with VA"
echo ""
echo "Option 3: Direct download"
echo "  - Upload to your server"
echo "  - Provide download link"
echo ""
echo "=========================================="
echo "✅ READY TO SEND!"
echo "=========================================="
echo ""
