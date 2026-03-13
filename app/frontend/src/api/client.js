import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Portfolio
export const getHoldings = () => api.get('/portfolio/holdings')
export const getSummary = () => api.get('/portfolio/summary')
export const getPortfolios = () => api.get('/portfolio/portfolios')
export const createPortfolio = (data) => api.post('/portfolio/portfolios', data)
export const deletePortfolio = (id) => api.delete(`/portfolio/portfolios/${id}`)
export const addHolding = (data) => api.post('/portfolio/holdings', data)
export const updateHolding = (id, data) => api.put(`/portfolio/holdings/${id}`, data)
export const deleteHolding = (id) => api.delete(`/portfolio/holdings/${id}`)

// Stocks
export const searchTicker = (q) => api.get('/stocks/search', { params: { q } })
export const getStock = (ticker) => api.get(`/stocks/${ticker}`)
export const getHistory = (ticker, period = '1y', interval = '1d') =>
  api.get(`/stocks/${ticker}/history`, { params: { period, interval } })
export const getAthAnalysis = (ticker) => api.get(`/stocks/${ticker}/ath`)
export const getEpsTrend = (ticker) => api.get(`/stocks/${ticker}/eps-trend`)
export const getEarningsEstimates = (ticker) => api.get(`/stocks/${ticker}/earnings-estimates`)
export const getGoogleTrends = (keywords, timeframe = 'today 12-m') =>
  api.get('/stocks/trends', { params: { keywords, timeframe } })
export const getFredSeries = (seriesId = 'DFF', period = '5y') =>
  api.get(`/macro/fred/${seriesId}`, { params: { period } })
export const getTechnicals = (ticker, period = '1y') =>
  api.get(`/stocks/${ticker}/technicals`, { params: { period } })
export const getFinancials = (ticker) => api.get(`/stocks/${ticker}/financials`)
export const compareStocks = (tickers, period = '1y') =>
  api.get('/stocks/compare', { params: { tickers, period } })
export const getReturns = (ticker, period = '1y') =>
  api.get(`/stocks/${ticker}/returns`, { params: { period } })
export const getRatioTrends = (ticker) => api.get(`/stocks/${ticker}/ratio-trends`)
export const getPeers = (ticker, tickers = '') =>
  api.get(`/stocks/${ticker}/peers`, { params: tickers ? { tickers } : {} })
export const getPeerGroup = (ticker) => api.get(`/stocks/${ticker}/peer-group`)
export const updatePeerGroup = (ticker, peers) => api.put(`/stocks/${ticker}/peer-group`, { peers })
export const getAnalystData = (ticker) => api.get(`/stocks/${ticker}/analyst`)
export const getEsgData = (ticker) => api.get(`/stocks/${ticker}/esg`)
export const getSentiment = (ticker) => api.get(`/stocks/${ticker}/sentiment`)
export const getEconomicCycle = (ticker) => api.get(`/stocks/${ticker}/economic-cycle`)
export const screenStocks = (filters = {}) => api.get('/stocks/screen', { params: filters })
export const getScreenOptions = () => api.get('/stocks/screen/options')
export const getBatchSignals = (tickers) => api.get('/stocks/signals', { params: { tickers } })
export const getUniverse = () => api.get('/stocks/universe')
export const addUniverseTickers = (tickers) => api.post('/stocks/universe', { tickers })
export const removeUniverseTicker = (ticker) => api.delete(`/stocks/universe/${ticker}`)

// Watchlist
export const getWatchlist = () => api.get('/watchlist')
export const addToWatchlist = (data) => api.post('/watchlist', data)
export const updateWatchlistItem = (id, data) => api.put(`/watchlist/${id}`, data)
export const removeFromWatchlist = (id) => api.delete(`/watchlist/${id}`)
export const convertToHolding = (id, data) => api.post(`/watchlist/${id}/convert`, data)

// Analytics
export const getPortfolioRisk = () => api.get('/analytics/portfolio-risk')
export const getPerformance = () => api.get('/analytics/performance')

// Thesis
export const getTheses = (status = '') => api.get('/thesis', { params: status ? { status } : {} })
export const createThesis = (data) => api.post('/thesis', data)
export const getThesis = (id) => api.get(`/thesis/${id}`)
export const updateThesis = (id, data) => api.put(`/thesis/${id}`, data)
export const deleteThesis = (id) => api.delete(`/thesis/${id}`)
export const addThesisCheckpoint = (id, data) => api.post(`/thesis/${id}/checkpoints`, data)
export const getThesisSnapshot = (id) => api.get(`/thesis/${id}/snapshot`)
