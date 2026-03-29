# Data Sources

## Distributor APIs

### DigiKey (Primary)
- **Use for**: Broadest parametric search, detailed component specs, lifecycle status
- **Provides**: pricing, stock levels, detailed parametric data, datasheet links, lifecycle status, package info
- **Strengths**: Most complete parametric database, reliable stock data
- **Limitations**: API rate limits, US-centric pricing

### Mouser (Secondary)
- **Use for**: Secondary stock check, alternative pricing, European availability
- **Provides**: pricing, stock levels, parametric data, datasheet links
- **Strengths**: Good European distribution, competitive pricing
- **Limitations**: Parametric search less flexible than DigiKey

### LCSC (Price-Optimized)
- **Use for**: High-volume production, cost-sensitive designs, Chinese-manufactured alternatives
- **Provides**: pricing (often lowest), stock levels, basic parametric data
- **Strengths**: Lowest prices for standard components, large stock of Chinese-brand equivalents
- **Limitations**: Fewer premium/specialty parts, less detailed parametric data

### Octopart (Aggregator)
- **Use for**: Cross-distributor price comparison, finding where a specific MPN is available
- **Provides**: aggregated pricing/stock across distributors, basic specs, datasheet links
- **Strengths**: Single query compares multiple distributors
- **Limitations**: Data may lag behind real-time stock, less parametric depth

## CAD Model Source

### SnapMagic
- **Use for**: Symbols, footprints, 3D models — AFTER component is selected from a distributor
- **Provides**: KiCad symbols/footprints, Altium symbols/footprints, STEP 3D models
- **Strengths**: Large library of verified CAD models
- **Limitations**: Not all components have models. Coverage varies.

## Critical Rule: Separation of Concerns

Component selection and CAD model sourcing are TWO SEPARATE STEPS:

1. **First**: Select the best component from distributor APIs based on electrical requirements, price, availability
2. **Then**: Check SnapMagic for CAD models of the selected component
3. **Never** select a component because it has a SnapMagic model
4. **Never** reject a component because it lacks a SnapMagic model — flag it as "no CAD model available" instead

## Search Strategy

```
User request
    │
    ├─ Distributor specified? ──YES──► Search ONLY that distributor
    │
    └─ No distributor specified
         │
         ├─ Priority: price ──► LCSC first, then DigiKey/Mouser, compare via Octopart
         │
         └─ Priority: availability ──► DigiKey first (largest stock), then Mouser, then LCSC
                                        Use Octopart to verify cross-distributor
```

After component selected → query SnapMagic for CAD models → report availability in recommendation.
