# 🔒 Full Potential Vault (SafeLink) - Public Utility Spec
> **Mission:** Secure, ephemeral secret sharing for the conscious ecosystem.
> **Utility:** Consumes Universal Credits (UC) for premium security features.

## 1. The Product
A standalone web service allows users to securely share sensitive data (API keys, credit cards, passwords) via ephemeral, encrypted links.

**Core Promise:**
- **Zero-Knowledge:** Data is encrypted on the client-side (future) or at rest (current).
- **Ephemeral:** Links burn after use. Logs are wiped.
- **Conscious:** Powered by the Full Potential OS.

## 2. Universal Credit (UC) Utility Model
We monetize trust and advanced security features using UC.

| Tier | Cost | Features |
| :--- | :--- | :--- |
| **Free** | 0 UC | 3 Links/Day, 24h Expiry, Text Only |
| **Pro** | 50 UC / mo | Unlimited Links, File Uploads (5MB), 7-Day Expiry |
| **Enterprise** | 500 UC / mo | Audit Logs, Custom Domain, Team Management |
| **Pay-Per-Link** | 1 UC / link | One-off premium link (Password Protected + Burn Notification) |

**Revenue Flow:**
User Wallet -> `SafeLink Service Wallet` -> `Treasury` (Burn/Distribute)

## 3. Architecture Evolution
Current state: Integrated module inside `Team Hub` (Port 8355).
Target state: Standalone Microservice `SafeLink` (Port 8360).

### 3.1 Decoupling Plan
1.  **Fork:** Extract `models.Vault*` and `api/vault/*` to new service.
2.  **Auth:** Implement "Guest Mode" (No login required for creation) + "Wallet Connect" (Log in with FP ID).
3.  **Frontend:** A simple, beautiful landing page (`vault.fullpotential.ai`).

### 3.2 Tech Stack
- **Backend:** FastAPI (lightweight).
- **Database:** SQLite (isolated) or Redis (for truly ephemeral).
- **Encryption:** `Fernet` (Symmetric) + `Client-Side AES` (for Zero-Knowledge claim).
- **Storage:** Local (files) or S3 (encrypted).

## 4. User Journey (Public)
1.  **Land:** User visits `vault.fullpotential.ai`.
2.  **Create:** Pastes secret -> Clicks "Encrypt".
3.  **Configure:**
    *   "Burn after 1 view" (Default)
    *   "Password Protect" (+1 UC or Login)
    *   "Notify me when read" (+1 UC or Login)
4.  **Pay:**
    *   If free: Generate Link.
    *   If premium: "Connect Wallet" or "Pay 1 UC".
5.  **Share:** Copy link.
6.  **Burn:** Recipient opens -> Data destroyed.

## 5. Growth Hack (Viral Loop)
*   **Footer:** Every shared link says: "Secured by Full Potential Vault. Get your free account."
*   **Incentive:** "Sign up and get 50 UC."

## 6. Roadmap
- [ ] **Phase 1 (Internal):** Dogfood current Vault in Team Portal (Done).
- [ ] **Phase 2 (Standalone):** Deploy `vault.fullpotential.ai` with Free Tier.
- [ ] **Phase 3 (Monetized):** Connect `CreditsClient` to charge for Password/Files.
- [ ] **Phase 4 (Zero-Knowledge):** Move encryption to browser (JS) so server never sees raw text.

---
**Status:** Ready for Phase 2 execution upon command.











