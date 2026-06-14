use anchor_lang::prelude::*;

declare_id!("TiE11111111111111111111111111111111111111111");

#[program]
pub mod sol_treasury {
    use super::*;

    /// Initialize the treasury
    /// Sets up the treasury account with authority and initial state
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        treasury.authority = ctx.accounts.authority.key();
        treasury.total_deposited = 0;
        treasury.total_withdrawn = 0;
        treasury.contract_count = 0;
        treasury.paused = false;
        treasury.bump = ctx.bumps.treasury;

        msg!("Treasury initialized with authority: {}", treasury.authority);

        Ok(())
    }

    /// Deposit SOL to the treasury
    /// Users call this to deposit SOL and receive TIE contracts (2x value)
    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(!treasury.paused, ErrorCode::TreasuryPaused);
        require!(amount > 0, ErrorCode::InvalidAmount);

        // Transfer SOL from depositor to treasury vault
        let cpi_context = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.depositor.to_account_info(),
                to: ctx.accounts.treasury_vault.to_account_info(),
            },
        );

        anchor_lang::system_program::transfer(cpi_context, amount)?;

        // Update treasury state
        treasury.total_deposited = treasury
            .total_deposited
            .checked_add(amount)
            .ok_or(ErrorCode::Overflow)?;

        treasury.contract_count = treasury
            .contract_count
            .checked_add(1)
            .ok_or(ErrorCode::Overflow)?;

        // Emit deposit event for indexing
        emit!(DepositEvent {
            depositor: ctx.accounts.depositor.key(),
            amount,
            contract_value: amount.checked_mul(2).ok_or(ErrorCode::Overflow)?,
            contract_id: treasury.contract_count,
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!(
            "Deposited {} lamports. Contract value: {} lamports. Contract ID: {}",
            amount,
            amount * 2,
            treasury.contract_count
        );

        Ok(())
    }

    /// Withdraw SOL from treasury (authorized only)
    /// Called by redemption service after approval
    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(!treasury.paused, ErrorCode::TreasuryPaused);
        require!(amount > 0, ErrorCode::InvalidAmount);

        // Verify authority
        require!(
            ctx.accounts.authority.key() == treasury.authority,
            ErrorCode::Unauthorized
        );

        // Calculate available balance
        let vault_balance = ctx.accounts.treasury_vault.lamports();
        require!(vault_balance >= amount, ErrorCode::InsufficientFunds);

        // Transfer SOL from treasury vault to recipient
        let bump = treasury.bump;
        let signer_seeds: &[&[&[u8]]] = &[&[b"treasury", &[bump]]];

        let cpi_context = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.treasury_vault.to_account_info(),
                to: ctx.accounts.recipient.to_account_info(),
            },
            signer_seeds,
        );

        anchor_lang::system_program::transfer(cpi_context, amount)?;

        // Update treasury state
        treasury.total_withdrawn = treasury
            .total_withdrawn
            .checked_add(amount)
            .ok_or(ErrorCode::Overflow)?;

        // Emit withdrawal event
        emit!(WithdrawEvent {
            recipient: ctx.accounts.recipient.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Withdrew {} lamports to {}", amount, ctx.accounts.recipient.key());

        Ok(())
    }

    /// Pause treasury (emergency only)
    /// Stops all deposits and withdrawals
    pub fn pause(ctx: Context<Pause>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(
            ctx.accounts.authority.key() == treasury.authority,
            ErrorCode::Unauthorized
        );

        treasury.paused = true;

        emit!(PauseEvent {
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Treasury paused by authority");

        Ok(())
    }

    /// Unpause treasury
    /// Resume normal operations after emergency
    pub fn unpause(ctx: Context<Pause>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(
            ctx.accounts.authority.key() == treasury.authority,
            ErrorCode::Unauthorized
        );

        treasury.paused = false;

        emit!(UnpauseEvent {
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Treasury unpaused by authority");

        Ok(())
    }

    /// Get treasury statistics
    /// View-only function for dashboard
    pub fn get_stats(ctx: Context<GetStats>) -> Result<TreasuryStats> {
        let treasury = &ctx.accounts.treasury;
        let vault_balance = ctx.accounts.treasury_vault.lamports();

        let treasury_ratio = if treasury.total_deposited > 0 {
            (vault_balance as f64) / (treasury.total_deposited as f64)
        } else {
            0.0
        };

        Ok(TreasuryStats {
            total_deposited: treasury.total_deposited,
            total_withdrawn: treasury.total_withdrawn,
            current_balance: vault_balance,
            treasury_ratio,
            contract_count: treasury.contract_count,
            paused: treasury.paused,
        })
    }
}

// ============================================================================
// Account Structures
// ============================================================================

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Treasury::LEN,
        seeds = [b"treasury"],
        bump
    )]
    pub treasury: Account<'info, Treasury>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump
    )]
    pub treasury: Account<'info, Treasury>,

    #[account(mut)]
    pub depositor: Signer<'info>,

    /// Treasury vault PDA that holds the SOL
    #[account(
        mut,
        seeds = [b"treasury"],
        bump
    )]
    pub treasury_vault: SystemAccount<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump
    )]
    pub treasury: Account<'info, Treasury>,

    pub authority: Signer<'info>,

    /// Treasury vault PDA
    #[account(
        mut,
        seeds = [b"treasury"],
        bump
    )]
    pub treasury_vault: SystemAccount<'info>,

    /// Recipient of withdrawal
    #[account(mut)]
    pub recipient: SystemAccount<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Pause<'info> {
    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump
    )]
    pub treasury: Account<'info, Treasury>,

    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct GetStats<'info> {
    #[account(seeds = [b"treasury"], bump = treasury.bump)]
    pub treasury: Account<'info, Treasury>,

    #[account(seeds = [b"treasury"], bump)]
    pub treasury_vault: SystemAccount<'info>,
}

// ============================================================================
// Data Structures
// ============================================================================

#[account]
pub struct Treasury {
    /// Authority that can pause/unpause and approve withdrawals
    pub authority: Pubkey,

    /// Total SOL deposited all-time (in lamports)
    pub total_deposited: u64,

    /// Total SOL withdrawn all-time (in lamports)
    pub total_withdrawn: u64,

    /// Total number of TIE contracts issued
    pub contract_count: u64,

    /// Emergency pause flag
    pub paused: bool,

    /// PDA bump seed
    pub bump: u8,
}

impl Treasury {
    pub const LEN: usize = 32 + // authority
                            8 +  // total_deposited
                            8 +  // total_withdrawn
                            8 +  // contract_count
                            1 +  // paused
                            1;   // bump
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct TreasuryStats {
    pub total_deposited: u64,
    pub total_withdrawn: u64,
    pub current_balance: u64,
    pub treasury_ratio: f64,
    pub contract_count: u64,
    pub paused: bool,
}

// ============================================================================
// Events
// ============================================================================

#[event]
pub struct DepositEvent {
    pub depositor: Pubkey,
    pub amount: u64,
    pub contract_value: u64,
    pub contract_id: u64,
    pub timestamp: i64,
}

#[event]
pub struct WithdrawEvent {
    pub recipient: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct PauseEvent {
    pub timestamp: i64,
}

#[event]
pub struct UnpauseEvent {
    pub timestamp: i64,
}

// ============================================================================
// Error Codes
// ============================================================================

#[error_code]
pub enum ErrorCode {
    #[msg("Treasury is currently paused")]
    TreasuryPaused,

    #[msg("Unauthorized: Only treasury authority can perform this action")]
    Unauthorized,

    #[msg("Invalid amount: Must be greater than zero")]
    InvalidAmount,

    #[msg("Insufficient funds in treasury")]
    InsufficientFunds,

    #[msg("Arithmetic overflow")]
    Overflow,
}
