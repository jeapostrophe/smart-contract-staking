from algopy import (
    ARC4Contract, 
    Account,
    Bytes,
    Global,
    GlobalState,
    Txn,
    UInt64,
    arc4,
    itxn,
    gtxn,
    subroutine,
    op
)
##################################################
# function: max (internal)
# arguments
# - a, a number
# - b, a number
# purpose: determine greater of two numbers
# pre-conditions: None
# post-conditions: None
# notes:
# - use ifs
##################################################
@subroutine
def max(a: UInt64, b: UInt64) -> UInt64:
    return a
##################################################
# function: min (internal)
# arguments
# - a, a number
# - b, a number
# purpose: determine greater of two numbers
# pre-conditions: None
# post-conditions: None
# notes:
# - use ifs
##################################################
@subroutine
def min(a: UInt64, b: UInt64) -> UInt64:
    return a
##################################################
class SmartContractStaking(ARC4Contract):
    ##############################################
    # function: __init__ (builtin)
    # arguments: None
    # purpose: construct initial state
    # pre-conditions: None
    # post-conditions: initial state set
    ##############################################
    def __init__(self) -> None:
        self.owner = Account()      # zero address
        self.funder = Account()     # zero address
        self.period = UInt64()      # 0
        self.funding = UInt64()     # 0
        self.total = UInt64()       # 0
    ##############################################
    # function: constructor
    # arguments:
    # - owner, who is the beneficiary
    # - funder, who is this
    # - total, total amount without lockup
    # purpose: create contract
    # pre-conditions: None
    # post-conditions: set owner and funder
    ##############################################
    @arc4.abimethod
    def setup(self, owner: arc4.Address) -> None:
        self.enforce_step(UInt64(0)) # Non-existant
        assert Txn.sender == Global.creator_address, "must be creator"
        self.funder = Txn.sender
        self.owner = owner.native
    ##############################################
    # function: configure
    # arguments:
    # - period, lockup period
    # purpose: set lockup period
    # pre-conditions
    # - funder and owner initialized
    # - period 0
    # post-conditions: set owner and funder
    ##############################################
    @arc4.abimethod
    def configure(self, period: arc4.UInt64) -> None:
        self.enforce_step(UInt64(1)) # Fresh
        self.require_owner()
        assert period > 0, "period must be greater than 0" 
        assert period <= 5, "period must be less than or equal to 0"
        self.period = period.native
    ##############################################
    # function: fill
    # arguments:
    # - total, how much to fill
    # purpose: fund it
    # pre-conditions
    # - period must be set
    # - funding and total must be uninitialized
    # - must be combined with pyament transaction
    #   for total amount
    # - must be only callable by funder 
    # post-conditions: 
    # - total and funding are set to arguments
    ##############################################
    @arc4.abimethod
    def fill(self, total: arc4.UInt64, funding: arc4.UInt64) -> None:
        self.enforce_step(UInt64(2)) # Ready
        self.require_funder()
        self.require_payment(self.funder, total.native)
        assert total > 0, "payment is greater than zero"
        self.total = total.native
        self.funding = funding.native
    ##############################################
    # function: participate
    # arguments:
    # - key registration params
    # purpose: allow contract to particpate in 
    #          consensus
    # pre-conditions
    # - must be callable by owner only
    # - must be combined with transaction transfering
    #   one fee into the contract account
    # post-conditions: 
    # - contract generates itnx for keyreg
    # notes:
    # - fee payment is to prevent potential draining
    #   into fees, even though it is not likely that
    #   a user may attempt to drain their funds
    # - MAB is not relevant due to the fee payment
    #   added
    ##############################################
    @arc4.abimethod
    def participate(self, vote_k: Bytes, sel_k: Bytes, vote_fst: arc4.UInt64, vote_lst: arc4.UInt64, vote_kd: arc4.UInt64, sp_key: Bytes) -> None: 
        self.enforce_step(UInt64(3)) # Full
        self.require_owner()
        self.require_payment(self.owner, UInt64(1000))
        itxn.KeyRegistration(
            vote_key=vote_k,
            selection_key=sel_k,
            vote_first=vote_fst.native,
            vote_last=vote_lst.native,
            vote_key_dilution=vote_kd.native,
            state_proof_key=sp_key,
            fee=1000
        ).submit()
    ##############################################
    # function: withdraw
    # arguments:
    # - amount
    # returns:
    # - next mab
    # purpose: extract funds from contract
    # pre-conditions
    # - only callable by owner
    # - let balance be the current balance of the
    #   contract
    # - let fee be one fee value
    # - balance - amount - fee >= mag
    # post-conditions: 
    # - transfer amount from the contract account
    #   to owner
    # notes:
    # - fee taken out of amount transfered to 
    #   owner
    # - can get amount available for withdra  by
    #   simulating zero withdraw
    ##############################################
    @arc4.abimethod
    def withdraw(self, amount: arc4.UInt64) -> UInt64:
        self.enforce_step(UInt64(3)) # Full
        self.require_owner()
        mab = self.calculate_mab()
        fee = UInt64(1000)
        balance = op.balance(Global.current_application_address)
        min_balance = op.Global.min_balance
        available_balance = balance - min_balance - fee
        assert amount <= available_balance, "amount must be less than or equal to balance"
        assert available_balance - amount.native >= mab, "mab available"
        itxn.Payment(
            amount=amount.native,
            receiver=Txn.sender,
        ).submit()
        return available_balance - mab - amount.native
    ##############################################
    # function: transfer
    # arguments:
    # - owner, new owner
    # purpose: change owner
    # pre-conditions
    # - only callable by the owner
    # post-conditions: 
    # - new owner
    # notes:
    # - fee taken out of amount transfered to 
    #   owner
    ##############################################
    @arc4.abimethod
    def transfer(self, owner: arc4.Address) -> None:
        self.enforce_step(UInt64(3)) # Full
        self.require_owner()
        assert self.owner != owner.native, "new owner must not be owner"
        self.owner = owner.native
    ##############################################
    # function: close
    # arguments: None
    # purpose: deletes contract
    # pre-conditions:
    # - mab is 0
    # post-conditions:
    # - contract is deleted
    # - account closed out to owner if it has a balance
    ##############################################
    @arc4.abimethod
    def close(self) -> None:
        self.enforce_step(UInt64(4)) # Full
        # assert Txn.sender is owner
        # assert mab is 0
        self.delete_application()
        # todo close app ...
    ##############################################
    # function: require_payment (internal)
    # arguments: None
    # purpose: check payment
    # pre-conditions: None
    # post-conditions: None
    ##############################################
    @subroutine
    def require_payment(self, who: Account, amount: UInt64) -> None:
        assert gtxn.PaymentTransaction(0).sender == who, "payment sender accurate"
        assert gtxn.PaymentTransaction(0).amount == amount, "payment amount accurate"
        assert gtxn.PaymentTransaction(0).receiver == Global.current_application_address, "payment receiver accurate"
    ##############################################
    # function: require_funder (internal)
    # arguments: None
    # purpose: check that sender is funder
    # pre-conditions: None
    # post-conditions: None
    ##############################################
    @subroutine
    def require_funder(self) -> None: 
        assert Txn.sender == self.funder, "must be funder" 
    ##############################################
    # function: require_owner (internal)
    # arguments: None
    # purpose: check that sender is owner
    # pre-conditions: None
    # post-conditions: None
    ##############################################
    @subroutine
    def require_owner(self) -> None: 
        assert Txn.sender == self.owner, "must be owner" 
    ##############################################
    # function: enforce_step (internal)
    # arguments:
    # - step, what step to enforce
    # purpose:
    # - enforce that method may be allowed in step
    # pre-conditions: None
    # post-conditions: None
    ##############################################
    @subroutine
    def enforce_step(self, n: UInt64) -> None:
        match n:
            case UInt64(0): # Non-existent
                assert self.funder == Global.zero_address, "funder must not be initialized"
                assert self.owner == Global.zero_address, "owner must not be initialized"
                assert self.period == 0, "period must not be initialize"
                assert self.funding == 0, "funding must not be initialize"
                assert self.total == 0, "total must not be initialized"
            case UInt64(1): # Fresh
                assert self.funder == Global.creator_address, "funder must be initialize" 
                assert self.owner != Global.zero_address, "owner must be initialized"
                assert self.period == 0, "period must not be initialized"
                assert self.funding == 0, "funding must not be initialized"
                assert self.total == 0, "total must not be initialized"
            case UInt64(2): # Ready
                assert self.funder == Global.creator_address, "funder must be initialize"
                assert self.owner != Global.zero_address, "owner must be initialized"
                assert self.period <= 5, "period within bounds" 
                assert self.funding == 0, "funding must not be initialized"
                assert self.total == 0, "total must not be initialized"
            case UInt64(3): # Full
                assert self.funder == Global.creator_address, "funder must be initialize"
                assert self.owner != Global.zero_address, "owner must be initialized"
                assert self.period <= 5, "period within bounds"
                assert self.funding > 0, "funding must be initialized"
                assert self.total > 0, "total must be initialized"
    ##############################################
    # function: delete_application (internal)
    # arguments: None
    # purpose: closes out balance to owner
    # pre-conditions:
    # - None
    # post-conditions:
    # - escrow balance zero
    ##############################################
    @subroutine
    def delete_application(self) -> None:
        itxn.Payment(
            receiver=Global.creator_address,
            close_remainder_to=self.owner
        ).submit()
    ##############################################
    # function: calculate_mab (internal)
    # arguments: None
    # purpose: calcualte minimum allowable balance
    # pre-conditions: None
    # post-conditions: None
    # notes:
    # - let period = number of months to to lockup
    #       total = total amount intially funded (airdrop + lockup bonus)
    #       y = lockup delays in months
    #       p = 1 / (self.period x 12) or 1 / (period)
    # - mimumum allowable balance =
    #     total x min(1, p x max(0, (period - (now() - funding + y x seconds-in-month)) / seconds-in-month))
    # - should be okay to distibute up to 166.67Mi
    #   which is over 5 times the highest airdrop
    #   amount (10Bi / 60 = 166.67Mi)
    ##############################################
    @subroutine
    def calculate_mab(self) -> UInt64:
        now = Global.latest_timestamp
        y = UInt64(12) # lockup delay
        seconds_in_month = UInt64(2628000)
        p = UInt64(12) * self.period # lockup period
        if now < self.funding + y * seconds_in_month: # before lockup (0 or funding)
            return self.funding 
        elif now > self.funding + (y + p) * seconds_in_month: # after lockup
            return UInt64(0)
        else: # during lockup
            m =  (now - (self.funding + y * seconds_in_month)) // seconds_in_month # elapsed months
            return (self.total * (p - m)) // p

