from fastapi import APIRouter, Query

from ..services.market_data import get_fred_series

router = APIRouter()


@router.get('/fred/{series_id}')
def fred_series(
    series_id: str,
    period: str = Query('5y', description='1mo/3mo/6mo/1y/2y/5y/ytd/max'),
):
    return get_fred_series(series_id=series_id, period=period)
