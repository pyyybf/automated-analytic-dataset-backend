from analyticsdf.analyticsdataframe import AnalyticsDataframe
import numpy as np


def generate_ad(seed=None):
    ad = AnalyticsDataframe(1000, 7, ["X1", "X2", "X3", "X4", "X5", "X6", "X6_weight"], "YYYY", seed=seed)

    covariance_matrix = np.array([[10, 9, 4],
                                  [9, 10, 6],
                                  [4, 6, 20]])
    ad.update_predictor_normal(predictor_name_list=["X1", "X2", "X3"],
                               mean=[100, 80, 120],
                               covariance_matrix=covariance_matrix)
    ad.update_predictor_uniform("X5", 0, 100)
    ad.update_predictor_categorical("X6", ["Red", "Yellow", "Blue"], [0.3, 0.4, 0.3])
    ad.update_predictor_multicollinear(target_predictor_name="X4",
                                       dependent_predictors_list=["X1", "X2"],
                                       beta=[0, 1, 1.5],
                                       epsilon_variance=20)

    # create a new predictor column, change categorical value into numerical value
    categorical_mapping_X6 = {"Red": 5, "Yellow": 1, "Blue": 1}
    ad.predictor_matrix["X6_weight"] = ad.predictor_matrix.replace({"X6": categorical_mapping_X6},
                                                                   inplace=False)["X6"]

    predictor_name_list = ["X1", "X3", "X6_weight"]
    polynomial_order = [1, 1, 1]
    beta = [100, 0, 1.5, 0]
    int_matrix = np.array([[0, 0, 0],
                           [0, 0, 0],
                           [1, 0, 0]])
    eps_var = 10
    ad.generate_response_vector_polynomial(predictor_name_list=predictor_name_list,
                                           polynomial_order=polynomial_order,
                                           beta=beta,
                                           interaction_term_betas=int_matrix,
                                           epsilon_variance=eps_var)
    ad.response_vector = np.exp(0.001 * ad.response_vector)
    return ad


ad = generate_ad()
df = ad.predictor_matrix
# df[ad.response_vector_name or "Y"] = ad.response_vector
print(str(ad.response_vector))
