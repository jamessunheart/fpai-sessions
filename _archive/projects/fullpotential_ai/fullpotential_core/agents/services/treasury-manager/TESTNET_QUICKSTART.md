# ⚡ FPAI Token - Testnet Quick Start

**Deploy and test in 10 minutes!**

---

## 🎯 What You Need

1. **Node.js** - [Download](https://nodejs.org/)
2. **MetaMask wallet** - [Install](https://metamask.io/)
3. **Sepolia ETH** (free) - [Get from faucet](https://sepoliafaucet.com/)
4. **Infura account** (free) - [Sign up](https://infura.io/)

---

## 🚀 5-Step Deployment

### **Step 1: Setup** (2 min)

```bash
cd /Users/jamessunheart/Development/agents/services/treasury-manager

# Install dependencies
npm install

# Setup environment
cp .env.testnet.example .env
```

Edit `.env` and add:
- Your Infura Sepolia RPC URL
- Your wallet private key (testnet wallet only!)
- Your Etherscan API key

### **Step 2: Get Testnet ETH** (3 min)

1. Go to https://sepoliafaucet.com/
2. Enter your wallet address
3. Complete verification
4. Wait for 0.5 ETH to arrive

Check balance:
```bash
npx hardhat run scripts/check-balance.js --network sepolia
```

### **Step 3: Compile** (30 sec)

```bash
npx hardhat compile
```

Should see: `Compiled 1 Solidity file successfully`

### **Step 4: Test Locally** (1 min)

```bash
npx hardhat test
```

Should see: `68 passing`

### **Step 5: Deploy to Sepolia** (2 min)

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

**Save the contract address from output!**

### **Bonus: Verify on Etherscan** (1 min)

```bash
npx hardhat verify --network sepolia <YOUR_CONTRACT_ADDRESS>
```

---

## ✅ Success!

Your FPAI Token is now live on Sepolia testnet!

**View on Etherscan:**
https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS

**What's deployed:**
- ✅ 100M FPAI tokens
- ✅ Token sale functionality
- ✅ Profit distribution system
- ✅ Buyback & burn mechanism
- ✅ Governance voting
- ✅ All security features

---

## 🧪 Quick Test

### **Test on Etherscan (No coding required!)**

1. Go to your contract on Sepolia Etherscan
2. Click "Contract" tab → "Write Contract"
3. Click "Connect to Web3" (connect MetaMask)

**Try these:**

**Start Sale:**
```
startSale() → Write → Confirm
```

**Buy Tokens:**
```
buyTokens()
payableAmount: 0.05
Write → Confirm
```

**Check Your Balance:**
- Click "Read Contract"
- `balanceOf(your_address)`
- You should see FPAI tokens!

**Add to MetaMask:**
- Open MetaMask
- Import tokens
- Paste contract address
- Symbol: FPAI
- See your tokens! 💎

---

## 🔥 What's Next?

### **For Testing:**
Run comprehensive tests:
```bash
npx hardhat run scripts/test-functions.js --network sepolia
```

### **For Production:**
1. Get smart contract audited ($10-25K)
2. Fix any audit findings
3. Deploy to mainnet
4. Launch token sale! 🚀

---

## 📚 Full Documentation

- **Complete Guide:** [TESTNET_DEPLOYMENT_GUIDE.md](TESTNET_DEPLOYMENT_GUIDE.md)
- **Token Strategy:** [FPAI_TOKEN_STRATEGY.md](FPAI_TOKEN_STRATEGY.md)
- **Launch Guide:** [TOKEN_LAUNCH_GUIDE.md](TOKEN_LAUNCH_GUIDE.md)
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## ❓ Troubleshooting

**"Insufficient funds"**
→ Get more Sepolia ETH from faucet

**"Contract not verified"**
→ Run verify command again with contract address

**"Nonce too high"**
→ Reset account in MetaMask (Settings > Advanced > Reset)

**Tests failing**
→ Run `npm install` again

---

## 💡 Pro Tips

- Use a NEW wallet for testnet (never your main wallet)
- Deploy during low gas times (weekends)
- Test extensively before mainnet
- Keep your private key secure
- Document everything

---

**Ready to revolutionize DeFi? Let's go! 🚀**
