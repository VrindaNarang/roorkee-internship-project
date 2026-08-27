import numpy as np

from prediction.evaluate import evaluate_classifier, evaluate_regressor


def test_evaluate_classifier_perfect_predictions():
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([1, 0, 1, 0])
    y_proba = np.array([0.9, 0.1, 0.8, 0.2])

    metrics = evaluate_classifier(y_true, y_pred, y_proba)
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["roc_auc"] == 1.0


def test_evaluate_classifier_single_class_skips_roc_auc():
    y_true = np.array([1, 1, 1])
    y_pred = np.array([1, 1, 0])
    y_proba = np.array([0.9, 0.8, 0.4])

    metrics = evaluate_classifier(y_true, y_pred, y_proba)
    assert metrics["roc_auc"] is None  # undefined with only one class present


def test_evaluate_regressor_perfect_predictions():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([100.0, 200.0, 300.0])

    metrics = evaluate_regressor(y_true, y_pred)
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["r2_score"] == 1.0


def test_evaluate_regressor_reports_error_magnitude():
    y_true = np.array([100.0, 200.0])
    y_pred = np.array([110.0, 190.0])

    metrics = evaluate_regressor(y_true, y_pred)
    assert metrics["mae"] == 10.0
