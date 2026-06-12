
// LINKEDIN AUTOMATION SCRIPT
// Run this in browser console on LinkedIn search page

const messages = [
  {
    "target": "Financial Advisors with CFP certification",
    "message": "Hi [Name] - Noticed your work in [specialty]. AI-powered lead matching for advisors - interested in quality HNW client leads? 20% commission only on close."
  },
  {
    "target": "Wealth Managers in SF Bay Area",
    "message": "Hi [Name] - Building AI matching for financial advisors. Your expertise in [specialty] caught my eye. Interested in pre-vetted client leads? Quick chat?"
  },
  {
    "target": "Fee-only Financial Planners",
    "message": "Hi [Name] - Love your fee-only approach. Created AI that matches clients to advisors like you. 20% commission, zero upfront cost. Curious?"
  }
];

const targets = [
    "financial advisor CFP San Francisco",
    "wealth manager Bay Area",
    "fee-only financial planner California"
];

console.log("🚀 LinkedIn Automation Ready");
console.log("1. Search for: " + targets[0]);
console.log("2. Click 'Connect' on profiles");
console.log("3. Use these messages:");
messages.forEach((msg, i) => {
    console.log(`\nTemplate ${i+1}:`);
    console.log(msg.message);
});

// Manual execution required - LinkedIn blocks automation
console.log("\n⚠️  LinkedIn blocks automation. Manual execution required.");
console.log("📋 Copy templates above and paste when sending connection requests");
