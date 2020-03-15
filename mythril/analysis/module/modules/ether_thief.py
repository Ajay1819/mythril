"""This module contains the detection code for unauthorized ether
withdrawal."""
import logging
from copy import copy

from mythril.analysis.module.base import DetectionModule, EntryPoint
from mythril.analysis.potential_issues import (
    get_potential_issues_annotation,
    PotentialIssue,
)
from mythril.laser.ethereum.transaction.symbolic import ACTORS
from mythril.analysis.swc_data import UNPROTECTED_ETHER_WITHDRAWAL
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.analysis import solver
from mythril.exceptions import UnsatError
from mythril.laser.smt import UGT

log = logging.getLogger(__name__)

DESCRIPTION = """
Search for cases where Ether can be withdrawn to a user-specified address.
An issue is reported if there is a valid end state where the attacker has successfully
increased their Ether balance.
"""


class EtherThief(DetectionModule):
    """This module search for cases where Ether can be withdrawn to a user-
    specified address."""

    name = "Attacker can profitably withdraw Ether from the contract account"
    swc_id = UNPROTECTED_ETHER_WITHDRAWAL
    description = DESCRIPTION
    entry_point = EntryPoint.CALLBACK
    post_hooks = ["CALL", "STATICCALL"]

    def reset_module(self):
        """
        Resets the module by clearing everything
        :return:
        """
        super().reset_module()

    def _execute(self, state: GlobalState) -> None:
        """
        :param state:
        :return:
        """
        if state.get_current_instruction()["address"] in self.cache:
            return
        potential_issues = self._analyze_state(state)

        annotation = get_potential_issues_annotation(state)
        annotation.potential_issues.extend(potential_issues)

    def _analyze_state(self, state):
        """
        :param state:
        :return:
        """
        state = copy(state)
        instruction = state.get_current_instruction()

        constraints = copy(state.world_state.constraints)

        constraints += [
            UGT(
                state.world_state.balances[ACTORS.attacker],
                state.world_state.starting_balances[ACTORS.attacker],
            )
        ]

        try:
            # Pre-solve so we only add potential issues if the attacker's balance is increased.

            solver.get_model(constraints)

            potential_issue = PotentialIssue(
                contract=state.environment.active_account.contract_name,
                function_name=state.environment.active_function_name,
                address=instruction["address"],
                swc_id=UNPROTECTED_ETHER_WITHDRAWAL,
                title="Unprotected Ether Withdrawal",
                severity="High",
                bytecode=state.environment.code.bytecode,
                description_head="Anyone can withdraw ETH from the contract account.",
                description_tail="Arbitrary senders other than the contract creator can withdraw ETH from the contract"
                + " account. This is likely to be a vulnerability.",
                detector=self,
                constraints=constraints,
            )

            return [potential_issue]
        except UnsatError:
            return []


detector = EtherThief()
