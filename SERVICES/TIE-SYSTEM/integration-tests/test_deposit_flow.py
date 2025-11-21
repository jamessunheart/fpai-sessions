"""
Integration Test: Deposit Flow

Tests the complete deposit flow across all 4 core services:
1. User deposits SOL to treasury
2. Treasury mints TIE contract NFT
3. Contract manager adds voting weight
4. Governance guardian monitors
"""

import pytest
import httpx
import asyncio
from datetime import datetime


# Service URLs
SOL_TREASURY_URL = "http://localhost:8920"
TIE_CONTRACT_URL = "http://localhost:8921"
VOTING_TRACKER_URL = "http://localhost:8922"
GOVERNANCE_GUARDIAN_URL = "http://localhost:8926"

# Test wallet
TEST_WALLET = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"


@pytest.mark.asyncio
async def test_deposit_creates_contract_and_voting_power():
    """
    Test happy path: Deposit → Contract → Voting
    """
    async with httpx.AsyncClient(timeout=30.0) as client:

        # Step 1: Check initial state
        print("\n1. Checking initial state...")

        # Get initial treasury balance
        treasury_response = await client.get(f"{SOL_TREASURY_URL}/treasury/balance")
        assert treasury_response.status_code == 200
        initial_balance = treasury_response.json()
        print(f"   Initial treasury: {initial_balance['current_balance']} SOL")

        # Get initial voting power
        voting_response = await client.get(f"{VOTING_TRACKER_URL}/voting/wallet/{TEST_WALLET}")
        assert voting_response.status_code == 200
        initial_votes = voting_response.json()
        print(f"   Initial voting power: {initial_votes['total_votes']} votes")

        # Step 2: Make deposit
        print("\n2. Depositing 10 SOL...")
        deposit_amount = 10.0
        deposit_request = {
            "wallet_address": TEST_WALLET,
            "amount_sol": deposit_amount,
            "signature": "test_signature_123"
        }

        deposit_response = await client.post(
            f"{SOL_TREASURY_URL}/treasury/deposit",
            json=deposit_request
        )
        assert deposit_response.status_code == 201
        deposit_data = deposit_response.json()
        print(f"   ✅ Deposit successful: {deposit_data['transaction_id']}")

        # Verify deposit data
        assert deposit_data["amount_sol"] == deposit_amount
        assert deposit_data["wallet_address"] == TEST_WALLET
        assert deposit_data["status"] == "confirmed"
        assert "tie_contract_value" in deposit_data
        assert deposit_data["tie_contract_value"] == deposit_amount * 2  # 2x value

        # Step 3: Wait for contract minting (async process)
        print("\n3. Waiting for contract minting...")
        await asyncio.sleep(2)  # Allow time for async contract creation

        # Step 4: Verify contract was created
        print("\n4. Verifying TIE contract...")
        contract_response = await client.get(f"{TIE_CONTRACT_URL}/contracts/{TEST_WALLET}")
        assert contract_response.status_code == 200
        contracts = contract_response.json()
        print(f"   Total contracts: {contracts['total_held']} held, {contracts['total_redeemed']} redeemed")

        # Find our new contract
        new_contracts = [c for c in contracts['held_contracts']
                        if c['sol_deposited'] == deposit_amount]
        assert len(new_contracts) >= 1
        new_contract = new_contracts[0]

        # Verify contract details
        assert new_contract['contract_value'] == deposit_amount * 2  # 2x
        assert new_contract['status'] == 'held'
        assert new_contract['voting_weight'] == 2
        print(f"   ✅ Contract minted: {new_contract['contract_id']}")
        print(f"      Value: {new_contract['contract_value']} SOL (2x)")
        print(f"      Voting weight: {new_contract['voting_weight']}")

        # Step 5: Verify voting power increased
        print("\n5. Verifying voting power increase...")
        voting_response = await client.get(f"{VOTING_TRACKER_URL}/voting/wallet/{TEST_WALLET}")
        assert voting_response.status_code == 200
        updated_votes = voting_response.json()

        # Should have +2 votes (holder)
        expected_total = initial_votes['total_votes'] + 2
        assert updated_votes['total_votes'] == expected_total
        assert updated_votes['holder_votes'] == initial_votes.get('holder_votes', 0) + 2
        print(f"   ✅ Voting power increased: {initial_votes['total_votes']} → {updated_votes['total_votes']}")
        print(f"      Holder votes: {updated_votes['holder_votes']}")
        print(f"      Seller votes: {updated_votes['seller_votes']}")

        # Step 6: Verify governance status
        print("\n6. Checking governance status...")
        governance_response = await client.get(f"{VOTING_TRACKER_URL}/voting/governance")
        assert governance_response.status_code == 200
        governance = governance_response.json()

        print(f"   Total votes: {governance['total_votes']}")
        print(f"   Holder control: {governance['holder_control_percentage']}%")
        print(f"   Stable: {governance['is_stable']}")

        # Should be stable (>51%)
        assert governance['is_stable'] == True
        assert governance['holder_control_percentage'] > 51.0

        # Step 7: Verify governance guardian sees it
        print("\n7. Verifying governance guardian monitoring...")
        guardian_response = await client.get(f"{GOVERNANCE_GUARDIAN_URL}/guardian/governance")
        assert guardian_response.status_code == 200
        guardian_data = guardian_response.json()

        print(f"   Guardian holder control: {guardian_data['holder_control_percentage']}%")
        print(f"   Threshold level: {guardian_data['threshold_level']}")
        print(f"   Stable: {guardian_data['is_stable']}")

        assert guardian_data['is_stable'] == True

        print("\n✅ DEPOSIT FLOW TEST PASSED")
        print("   Deposit → Contract → Voting → Governance monitoring all working correctly")


@pytest.mark.asyncio
async def test_multiple_deposits_cumulative_voting():
    """
    Test that multiple deposits accumulate voting power correctly.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:

        print("\n1. Getting initial voting power...")
        initial_response = await client.get(f"{VOTING_TRACKER_URL}/voting/wallet/{TEST_WALLET}")
        assert initial_response.status_code == 200
        initial_votes = initial_response.json()['total_votes']
        print(f"   Initial: {initial_votes} votes")

        # Make 3 deposits
        num_deposits = 3
        deposit_amount = 5.0

        print(f"\n2. Making {num_deposits} deposits of {deposit_amount} SOL each...")
        for i in range(num_deposits):
            deposit_request = {
                "wallet_address": TEST_WALLET,
                "amount_sol": deposit_amount,
                "signature": f"test_signature_{i}"
            }

            response = await client.post(
                f"{SOL_TREASURY_URL}/treasury/deposit",
                json=deposit_request
            )
            assert response.status_code == 201
            print(f"   ✅ Deposit {i+1} successful")

            await asyncio.sleep(1)  # Allow processing

        # Wait for all contracts to be minted
        print("\n3. Waiting for contract minting...")
        await asyncio.sleep(3)

        # Check final voting power
        print("\n4. Checking final voting power...")
        final_response = await client.get(f"{VOTING_TRACKER_URL}/voting/wallet/{TEST_WALLET}")
        assert final_response.status_code == 200
        final_votes = final_response.json()['total_votes']

        expected_increase = num_deposits * 2  # Each deposit = 2 votes
        expected_total = initial_votes + expected_increase

        print(f"   Expected: {expected_total} votes")
        print(f"   Actual: {final_votes} votes")

        assert final_votes == expected_total
        print(f"\n✅ CUMULATIVE VOTING TEST PASSED")


@pytest.mark.asyncio
async def test_governance_monitoring_after_deposits():
    """
    Test that governance guardian correctly monitors after deposits.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:

        # Make a deposit
        print("\n1. Making deposit...")
        deposit_request = {
            "wallet_address": TEST_WALLET,
            "amount_sol": 15.0,
            "signature": "test_sig"
        }

        deposit_response = await client.post(
            f"{SOL_TREASURY_URL}/treasury/deposit",
            json=deposit_request
        )
        assert deposit_response.status_code == 201

        # Wait for guardian to poll (30 second interval)
        print("\n2. Waiting for governance guardian to poll...")
        await asyncio.sleep(35)

        # Check guardian status
        print("\n3. Checking guardian status...")
        guardian_response = await client.get(f"{GOVERNANCE_GUARDIAN_URL}/guardian/status")
        assert guardian_response.status_code == 200
        guardian_status = guardian_response.json()

        print(f"   Monitoring active: {guardian_status['monitoring_active']}")
        print(f"   Last check: {guardian_status['last_check']}")
        print(f"   Current holder control: {guardian_status['current_holder_control']}%")
        print(f"   Governance level: {guardian_status['governance_level']}")
        print(f"   System status: {guardian_status['system_status']}")
        print(f"   Alerts active: {guardian_status['alerts_active']}")

        # Verify guardian is monitoring
        assert guardian_status['monitoring_active'] == True
        assert guardian_status['last_check'] is not None
        assert guardian_status['system_status'] == "operational"

        # Check governance events
        print("\n4. Checking governance events (audit log)...")
        events_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/events?limit=10"
        )
        assert events_response.status_code == 200
        events = events_response.json()['events']

        print(f"   Recent events: {len(events)}")
        if events:
            latest = events[0]
            print(f"   Latest: {latest['event_type']} @ {latest['timestamp']}")
            print(f"   Action: {latest['action']}")
            print(f"   Holder control: {latest['holder_control']}%")

        print(f"\n✅ GOVERNANCE MONITORING TEST PASSED")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
