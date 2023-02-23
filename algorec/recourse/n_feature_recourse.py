from copy import deepcopy
import numpy as np


class NFeatureRecourse:
    def __init__(self, model, n_features=None, threshold=0.5):
        self.model = model
        self.n_features = n_features
        self.threshold = threshold

    def _get_coefficients(self):
        """Utility function to retrieve model parameters."""

        model = deepcopy(self.model)
        intercept = self.model.intercept_
        coefficients = self.model.coef_

        # Adjusting the intercept to match the desired threshold.
        intercept = intercept - np.log(self.threshold / (1 - self.threshold))
        model.intercept_ = intercept

        return intercept, coefficients, model

    def _counterfactual(self, agent, action_set):
        intercept, coefficients, model = self._get_coefficients()

        # Do not change if the agent is over the threshold
        if self.model.predict_proba(agent.to_frame().T)[0, -1] >= self.threshold:
            return agent

        # Get base vector
        base_vector = coefficients.copy().squeeze()
        n_features = (
            base_vector.shape[0] if self.n_features is None else self.n_features
        )

        is_usable = np.array([
            action_set[col].step_direction in [np.sign(coeff), 0]
            and action_set[col].actionable
            for col, coeff in zip(agent.index, base_vector)
        ])
        base_vector[~is_usable] = 0

        # Use features with highest contribution towards the threshold
        rejected_features = np.argsort(np.abs(base_vector))[:-n_features]
        base_vector[rejected_features] = 0

        base_vector = base_vector / np.linalg.norm(base_vector)
        reg_target = -intercept
        multiplier = (reg_target - np.dot(agent.values, coefficients.T)) / np.dot(
            base_vector, coefficients.T
        )
        counterfactual = agent + multiplier * base_vector

        return counterfactual

    def counterfactual(self, population):
        action_set = population.action_set_

        counterfactual_examples = population.data.apply(
            lambda agent: self._counterfactual(agent, action_set), axis=1
        )

        return counterfactual_examples
