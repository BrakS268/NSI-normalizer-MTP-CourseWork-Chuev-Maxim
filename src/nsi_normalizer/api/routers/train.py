from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from nsi_normalizer.api.dependencies import verify_api_key
from nsi_normalizer.api.schemas import TrainResponse

router = APIRouter()


@router.post(
    "/",
    response_model=TrainResponse,
    summary="Train deduplication classifier on labeled pairs CSV",
)
async def train_classifier(
    file: UploadFile = File(..., description="CSV with labeled pairs (left_code, left_name, right_code, right_name, label)"),
    _: str = Depends(verify_api_key),
) -> TrainResponse:
    """Upload a labeled pairs CSV and train the GradientBoosting classifier.

    CSV format (columns):
      left_code, left_name, left_description,
      right_code, right_name, right_description,
      label  (1 = duplicate, 0 = not duplicate)
    """
    from pathlib import Path
    from nsi_normalizer.ml.training.trainer import train

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .csv files are accepted",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )

    try:
        model_path = Path("/app/models/dedup_classifier.joblib")
        metrics = train(contents, model_path=model_path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {e}",
        ) from e

    return TrainResponse(
        status="trained",
        n_samples=metrics["n_samples"],
        f1_mean=round(metrics["f1_mean"], 4),
        f1_std=round(metrics["f1_std"], 4),
        model_path=str(model_path),
    )
