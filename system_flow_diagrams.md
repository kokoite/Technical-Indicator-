# System Flow Diagrams

## 1. Overall System Architecture Flow

```mermaid
graph TB
    subgraph "Data Sources"
        NSE[NSE Website]
        YF[Yahoo Finance API]
        DB[(Stock Database)]
    end
    
    subgraph "Core Processing"
        SLM[Stock List Manager]
        TIC[Technical Indicator Calculator]
        BSA[Buy/Sell Signal Analyzer]
        ESS[Enhanced Strategy Screener]
    end
    
    subgraph "Management Layer"
        ARM[Advanced Recommendation Manager]
        WAS[Weekly Analysis System]
        DM[Daily Monitor]
        FA[Friday Analyzer]
    end
    
    subgraph "Storage"
        RDB[(Recommendations DB)]
        PDB[(Performance DB)]
        WDB[(Watchlist DB)]
    end
    
    subgraph "Outputs"
        DR[Daily Reports]
        WR[Weekly Reports]
        PR[Performance Reports]
    end
    
    NSE --> SLM
    YF --> TIC
    DB --> SLM
    
    SLM --> ESS
    TIC --> BSA
    BSA --> ESS
    ESS --> ARM
    
    ARM --> RDB
    ARM --> PDB
    ARM --> WDB
    
    WAS --> ESS
    WAS --> ARM
    DM --> ARM
    FA --> ARM
    FA --> WAS
    
    DM --> DR
    FA --> WR
    ARM --> PR
    
    RDB --> DM
    RDB --> FA
    PDB --> DM
    WDB --> DM
```

## 2. Daily Monitoring Flow (Monday-Thursday)

```mermaid
flowchart TD
    Start([Daily Monitor Start]) --> CheckDay{Is it Mon-Thu?}
    CheckDay -->|No| Weekend[Weekend - No Monitoring]
    CheckDay -->|Yes| Step1[Step 1: Monitor STRONG Recommendations]
    
    Step1 --> GetStrong[Get STRONG Recommendations from DB]
    GetStrong --> BatchPrice1[Batch Fetch Current Prices]
    BatchPrice1 --> CheckCriteria{Check Selling Criteria}
    
    CheckCriteria --> HardScore{Score < 50?}
    HardScore -->|Yes| SellHard[Sell - Hard Score Check]
    HardScore -->|No| Loss7{Loss >= 7%?}
    Loss7 -->|Yes| SellLoss7[Sell - 7% Stop Loss]
    Loss7 -->|No| Loss5{Loss >= 5%?}
    Loss5 -->|Yes| CheckIndicators{Score < 35?}
    CheckIndicators -->|Yes| SellLoss5[Sell - 5% Loss + Weak Indicators]
    CheckIndicators -->|No| Hold1[Hold - Indicators OK]
    Loss5 -->|No| Hold2[Hold - Within Limits]
    
    SellHard --> AddWatchlist1[Add to Sold Watchlist]
    SellLoss7 --> AddWatchlist1
    SellLoss5 --> AddWatchlist1
    
    AddWatchlist1 --> Step2[Step 2: Check WEAK Promotions]
    Hold1 --> Step2
    Hold2 --> Step2
    
    Step2 --> GetWeak[Get WEAK Recommendations]
    GetWeak --> BatchPrice2[Batch Fetch Current Prices]
    BatchPrice2 --> CheckPromotion{Price up >= 2% since Friday?}
    CheckPromotion -->|Yes| ReAnalyze[Re-analyze with Current Indicators]
    CheckPromotion -->|No| NoPromotion[No Promotion]
    
    ReAnalyze --> CheckScore{Score >= 70?}
    CheckScore -->|Yes| Promote[Promote WEAK to STRONG]
    CheckScore -->|No| StillWeak[Still WEAK]
    
    Promote --> Step25[Step 2.5: Check Sold Stocks Re-entry]
    NoPromotion --> Step25
    StillWeak --> Step25
    
    Step25 --> GetSold[Get Sold Stocks Watchlist]
    GetSold --> BatchPrice3[Batch Fetch Current Prices]
    BatchPrice3 --> CheckReentry{Score >= 60?}
    CheckReentry -->|Yes| ReEnter[Re-enter as STRONG]
    CheckReentry -->|No| UpdateWatch[Update Watchlist Check]
    
    ReEnter --> RemoveWatch[Remove from Watchlist]
    RemoveWatch --> Step3[Step 3: Update Performance Data]
    UpdateWatch --> Step3
    
    Step3 --> GetActive[Get All Active Recommendations]
    GetActive --> BatchPrice4[Batch Update Performance]
    BatchPrice4 --> Step4[Step 4: Generate Daily Report]
    
    Step4 --> ShowTiers[Show Current Tier Distribution]
    ShowTiers --> ShowActivity[Show Today's Activity]
    ShowActivity --> ShowPerformance[Show STRONG Performance]
    ShowPerformance --> End([Daily Monitor Complete])
    
    Weekend --> End
```

## 3. Friday Analysis Flow

```mermaid
flowchart TD
    Start([Friday Analyzer Start]) --> CheckDay{Is it Friday or Force Run?}
    CheckDay -->|No| NotFriday[Not Friday - Use daily_monitor.py]
    CheckDay -->|Yes| Step1[Step 1: Cleanup STRONG Recommendations]
    
    Step1 --> GetStrong[Get All STRONG Recommendations]
    GetStrong --> BatchPrice1[Batch Fetch Current Prices]
    BatchPrice1 --> CheckCleanup{Check Cleanup Criteria}
    
    CheckCleanup --> Loss5Week{Loss >= 5% after 1 week?}
    Loss5Week -->|Yes| CleanupWeek[Cleanup - Weekly Loss]
    Loss5Week -->|No| Loss3BiWeek{Loss >= 3% after 2 weeks?}
    Loss3BiWeek -->|Yes| CleanupBiWeek[Cleanup - Bi-weekly Loss]
    Loss3BiWeek -->|No| NoGrowth{< 2% gain after 30 days?}
    NoGrowth -->|Yes| CleanupMonth[Cleanup - Monthly Stagnation]
    NoGrowth -->|No| Keep[Keep Position]
    
    CleanupWeek --> AddWatchlist2[Add to Sold Watchlist]
    CleanupBiWeek --> AddWatchlist2
    CleanupMonth --> AddWatchlist2
    
    AddWatchlist2 --> Step2[Step 2: Update Friday Prices]
    Keep --> Step2
    
    Step2 --> GetWeakHold[Get WEAK/HOLD Recommendations]
    GetWeakHold --> BatchPrice2[Pure Batch Price Updates]
    BatchPrice2 --> UpdateFridayPrices[Update Friday Reference Prices]
    UpdateFridayPrices --> Step3[Step 3: Run Weekly Analysis]
    
    Step3 --> WeeklyAnalysis[Run Full Weekly Analysis]
    WeeklyAnalysis --> ClassifyTiers[Classify by Tiers]
    ClassifyTiers --> SaveRecs[Save Tiered Recommendations]
    SaveRecs --> Step4[Step 4: Generate Weekly Report]
    
    Step4 --> RealizedPerf[Show Realized Performance]
    RealizedPerf --> UnrealizedPerf[Show Unrealized Performance]
    UnrealizedPerf --> TierDist[Show Tier Distribution]
    TierDist --> WeeklyActivity[Show Weekly Activity]
    WeeklyActivity --> End([Friday Analysis Complete])
    
    NotFriday --> End
```

## 4. Weekly Analysis System Flow

```mermaid
flowchart TD
    Start([Weekly Analysis Start]) --> GetStocks[Get All NSE Stocks]
    GetStocks --> BatchFetch[Pure Batch Fetch - 100 stocks/batch]
    BatchFetch --> FilterPrice[Filter Price Range 50-1000]
    FilterPrice --> ProcessBatches[Process in Batches of 50]
    
    ProcessBatches --> MiniBatch[Create Mini-batches of 3]
    MiniBatch --> ThreadAnalysis[Thread Analysis - 2 workers max]
    ThreadAnalysis --> SingleAnalysis[Analyze Single Stock]
    
    SingleAnalysis --> GetIndicators[Calculate Technical Indicators]
    GetIndicators --> SignalAnalysis[Buy/Sell Signal Analysis]
    SignalAnalysis --> ScoreCalculation[Calculate Weighted Score]
    ScoreCalculation --> CheckMinScore{Score >= Min Threshold?}
    
    CheckMinScore -->|Yes| AddResult[Add to Results]
    CheckMinScore -->|No| Skip[Skip Stock]
    
    AddResult --> MoreStocks{More Stocks?}
    Skip --> MoreStocks
    MoreStocks -->|Yes| MiniBatch
    MoreStocks -->|No| SortResults[Sort by Score Descending]
    
    SortResults --> SaveResults[Save to Database]
    SaveResults --> GenerateReport[Generate Weekly Report]
    GenerateReport --> ScoreDistribution[Show Score Distribution]
    ScoreDistribution --> TopPerformers[Show Top 10 Performers]
    TopPerformers --> SectorAnalysis[Analyze Sector Performance]
    SectorAnalysis --> SaveSummary[Save Weekly Summary]
    SaveSummary --> End([Weekly Analysis Complete])
```

## 5. Technical Indicator Calculation Flow

```mermaid
flowchart TD
    Start([Calculate Indicators]) --> FetchData[Single API Call - 2 Years Data]
    FetchData --> CheckData{Data Available?}
    CheckData -->|No| Return[Return None]
    CheckData -->|Yes| CalcDMA[Calculate DMA 50 & 200]
    
    CalcDMA --> WeeklyResample[Resample to Weekly Data]
    WeeklyResample --> CalcMACD[Calculate Weekly MACD]
    CalcMACD --> CalcRSI[Calculate Weekly RSI]
    CalcRSI --> CalcOBV[Calculate OBV]
    CalcOBV --> CalcVPT[Calculate VPT]
    CalcVPT --> CalcPriceChanges[Calculate Price Changes]
    CalcPriceChanges --> CalcWeeklyPrices[Calculate Weekly Price Data]
    CalcWeeklyPrices --> CompileResults[Compile All Results]
    CompileResults --> Return
```

## 6. Buy/Sell Signal Analysis Flow

```mermaid
flowchart TD
    Start([Signal Analysis]) --> GetIndicators[Get Technical Indicators]
    GetIndicators --> TrendAnalysis[Analyze Trend Signals - 25%]
    
    TrendAnalysis --> DMA50{50-DMA Trend?}
    DMA50 -->|Uptrend| AddTrend8[+8 Points]
    DMA50 -->|Downtrend| SubTrend5[-5 Points]
    
    AddTrend8 --> DMA200{200-DMA Trend?}
    SubTrend5 --> DMA200
    DMA200 -->|Uptrend| AddTrend7[+7 Points]
    DMA200 -->|Downtrend| SubTrend3[-3 Points]
    
    AddTrend7 --> PriceVsDMA{Price vs 50-DMA?}
    SubTrend3 --> PriceVsDMA
    PriceVsDMA -->|Above| AddPrice5[+5 Points]
    PriceVsDMA -->|Below| SubPrice3[-3 Points]
    
    AddPrice5 --> GoldenCross{50-DMA vs 200-DMA?}
    SubPrice3 --> GoldenCross
    GoldenCross -->|Golden Cross| AddGold5[+5 Points]
    GoldenCross -->|Death Cross| SubGold5[-5 Points]
    
    AddGold5 --> MomentumAnalysis[Analyze Momentum - 20%]
    SubGold5 --> MomentumAnalysis
    
    MomentumAnalysis --> MACDCross{Recent MACD Crossover?}
    MACDCross -->|Bullish| AddMomentum12[+12 Points]
    MACDCross -->|Bearish| SubMomentum12[-12 Points]
    MACDCross -->|None| MACDHist{MACD Histogram?}
    
    AddMomentum12 --> RSIAnalysis[Analyze RSI - 15%]
    SubMomentum12 --> RSIAnalysis
    MACDHist -->|Strong Positive| AddHist5[+5 Points]
    MACDHist -->|Weak Negative| SubHist5[-5 Points]
    
    AddHist5 --> RSIAnalysis
    SubHist5 --> RSIAnalysis
    
    RSIAnalysis --> RSILevel{RSI Level?}
    RSILevel -->|30-45| AddRSI10[+10 Points - Oversold Recovery]
    RSILevel -->|45-65| AddRSI5[+5 Points - Healthy]
    RSILevel -->|65-75| SubRSI3[-3 Points - Getting Overbought]
    RSILevel -->|>75| SubRSI8[-8 Points - Overbought]
    RSILevel -->|<30| AddRSI8[+8 Points - Oversold]
    
    AddRSI10 --> VolumeAnalysis[Analyze Volume - 25%]
    AddRSI5 --> VolumeAnalysis
    SubRSI3 --> VolumeAnalysis
    SubRSI8 --> VolumeAnalysis
    AddRSI8 --> VolumeAnalysis
    
    VolumeAnalysis --> OBVTrend{OBV Trend?}
    OBVTrend -->|Strong Up >15%| AddOBV8[+8 Points]
    OBVTrend -->|Up 5-15%| AddOBV5[+5 Points]
    OBVTrend -->|Strong Down <-15%| SubOBV8[-8 Points]
    OBVTrend -->|Down -5 to -15%| SubOBV5[-5 Points]
    
    AddOBV8 --> VPTTrend{VPT Trend?}
    AddOBV5 --> VPTTrend
    SubOBV8 --> VPTTrend
    SubOBV5 --> VPTTrend
    
    VPTTrend -->|Strong Up >15%| AddVPT8[+8 Points]
    VPTTrend -->|Up 5-15%| AddVPT5[+5 Points]
    VPTTrend -->|Strong Down <-15%| SubVPT8[-8 Points]
    VPTTrend -->|Down -5 to -15%| SubVPT5[-5 Points]
    
    AddVPT8 --> PriceAction[Analyze Price Action - 15%]
    AddVPT5 --> PriceAction
    SubVPT8 --> PriceAction
    SubVPT5 --> PriceAction
    
    PriceAction --> RecentMomentum{Recent 4-week Avg Change?}
    RecentMomentum -->|>2%| AddPrice8[+8 Points - Strong]
    RecentMomentum -->|>0%| AddPrice4[+4 Points - Positive]
    RecentMomentum -->|<-2%| SubPrice8[-8 Points - Weak]
    RecentMomentum -->|<0%| SubPrice4[-4 Points - Negative]
    
    AddPrice8 --> WeightedScore[Calculate Weighted Scores]
    AddPrice4 --> WeightedScore
    SubPrice8 --> WeightedScore
    SubPrice4 --> WeightedScore
    
    WeightedScore --> TotalScore[Sum Total Score]
    TotalScore --> Recommendation{Score Range?}
    
    Recommendation -->|>=75| StrongBuy[STRONG BUY - Low Risk]
    Recommendation -->|60-74| Buy[BUY - Low-Medium Risk]
    Recommendation -->|40-59| WeakBuy[WEAK BUY - Medium Risk]
    Recommendation -->|20-39| Hold[HOLD - Medium-High Risk]
    Recommendation -->|<20| Sell[SELL - High Risk]
    
    StrongBuy --> Return[Return Analysis Result]
    Buy --> Return
    WeakBuy --> Return
    Hold --> Return
    Sell --> Return
```

## 7. Database Operations Flow

```mermaid
flowchart TD
    Start([Database Operation]) --> Operation{Operation Type?}
    
    Operation -->|Save Recommendation| SaveRec[Save Recommendation]
    Operation -->|Update Performance| UpdatePerf[Update Performance]
    Operation -->|Promote WEAK| PromoteWeak[Promote to STRONG]
    Operation -->|Sell STRONG| SellStrong[Sell Position]
    
    SaveRec --> CheckDuplicate{Duplicate Exists?}
    CheckDuplicate -->|No| InsertNew[Insert New Record]
    CheckDuplicate -->|Yes| CheckScore{Better Score?}
    CheckScore -->|Yes| UpdateExisting[Update Existing]
    CheckScore -->|No| SkipDuplicate[Skip Duplicate]
    
    InsertNew --> SetTier{Determine Tier}
    SetTier -->|Score >=70| SetStrong[Set STRONG]
    SetTier -->|Score 50-69| SetWeak[Set WEAK]
    SetTier -->|Score <50| SetHold[Set HOLD]
    
    SetStrong --> CalculateLevels[Calculate Target/Stop Loss]
    SetWeak --> CalculateLevels
    SetHold --> CalculateLevels
    
    CalculateLevels --> CommitSave[Commit to Database]
    UpdateExisting --> CommitSave
    SkipDuplicate --> End([Operation Complete])
    
    UpdatePerf --> GetActiveRecs[Get Active Recommendations]
    GetActiveRecs --> BatchPrices[Batch Fetch Current Prices]
    BatchPrices --> CalcReturns[Calculate Returns]
    CalcReturns --> UpdatePerfTable[Update Performance Table]
    UpdatePerfTable --> CheckTargets{Target/Stop Hit?}
    CheckTargets -->|Yes| ClosePosition[Close Position]
    CheckTargets -->|No| KeepActive[Keep Active]
    
    PromoteWeak --> UpdateTier[Update Tier to STRONG]
    UpdateTier --> UpdateEntry[Update Entry Price]
    UpdateEntry --> SetPromotionDate[Set Promotion Date]
    
    SellStrong --> CalcPnL[Calculate P&L]
    CalcPnL --> UpdateSellInfo[Update Sell Information]
    UpdateSellInfo --> AddToWatchlist[Add to Sold Watchlist]
    
    CommitSave --> End
    ClosePosition --> End
    KeepActive --> End
    SetPromotionDate --> End
    AddToWatchlist --> End
```

## 8. Error Handling and Resilience Flow

```mermaid
flowchart TD
    Start([System Operation]) --> TryOperation[Try Main Operation]
    TryOperation --> Success{Operation Successful?}
    
    Success -->|Yes| LogSuccess[Log Success]
    Success -->|No| ErrorType{Error Type?}
    
    ErrorType -->|API Failure| APIError[API Error Handler]
    ErrorType -->|Database Error| DBError[Database Error Handler]
    ErrorType -->|Data Validation| ValidationError[Validation Error Handler]
    ErrorType -->|Network Timeout| TimeoutError[Timeout Error Handler]
    
    APIError --> TryFallback{Fallback Available?}
    TryFallback -->|Yes| UseFallback[Use Fallback Source]
    TryFallback -->|No| LogAPIError[Log API Error]
    
    UseFallback --> FallbackSuccess{Fallback Successful?}
    FallbackSuccess -->|Yes| LogFallbackSuccess[Log Fallback Success]
    FallbackSuccess -->|No| LogFallbackFail[Log Fallback Failure]
    
    DBError --> RetryDB{Retry Available?}
    RetryDB -->|Yes| RetryOperation[Retry Database Operation]
    RetryDB -->|No| LogDBError[Log Database Error]
    
    RetryOperation --> RetrySuccess{Retry Successful?}
    RetrySuccess -->|Yes| LogRetrySuccess[Log Retry Success]
    RetrySuccess -->|No| LogRetryFail[Log Retry Failure]
    
    ValidationError --> SkipRecord[Skip Invalid Record]
    SkipRecord --> LogValidationError[Log Validation Error]
    
    TimeoutError --> IncreaseTimeout[Increase Timeout]
    IncreaseTimeout --> RetryWithTimeout[Retry with Longer Timeout]
    RetryWithTimeout --> TimeoutSuccess{Timeout Retry Successful?}
    TimeoutSuccess -->|Yes| LogTimeoutSuccess[Log Timeout Success]
    TimeoutSuccess -->|No| LogTimeoutFail[Log Timeout Failure]
    
    LogSuccess --> Continue[Continue Processing]
    LogFallbackSuccess --> Continue
    LogRetrySuccess --> Continue
    LogTimeoutSuccess --> Continue
    
    LogAPIError --> GracefulDegrade[Graceful Degradation]
    LogFallbackFail --> GracefulDegrade
    LogDBError --> GracefulDegrade
    LogRetryFail --> GracefulDegrade
    LogValidationError --> Continue
    LogTimeoutFail --> GracefulDegrade
    
    GracefulDegrade --> PartialResults[Return Partial Results]
    PartialResults --> End([Operation Complete with Errors])
    Continue --> End([Operation Complete Successfully])
```

These flow diagrams provide a comprehensive view of how your stock monitoring and recommendation system operates, showing the detailed logic flow for each major component and their interactions.