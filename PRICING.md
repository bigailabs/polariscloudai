# Polaris Computer Pricing

## Overview

Polaris Computer provides GPU compute resources from multiple cloud providers through a unified platform. Pricing includes a 20% markup on provider costs.

## Pricing Formula

```
Customer Price = Provider Cost × 1.20 (20% markup)
```

## Markup Rationale

The 20% markup covers:
- **Platform maintenance and support** - 24/7 monitoring, incident response
- **Unified multi-provider interface** - Single dashboard for Verda, Targon, and future providers
- **SSH key management** - Automatic key provisioning and rotation
- **Usage monitoring** - Real-time metrics and cost tracking
- **Billing consolidation** - One invoice for all providers

## GPU Pricing Examples

| GPU | Provider Cost | Customer Price |
|-----|---------------|----------------|
| Tesla V100 16GB | $0.076/hr | $0.091/hr |
| RTX A6000 48GB | $0.162/hr | $0.194/hr |
| A100 40GB | $0.238/hr | $0.286/hr |
| A100 80GB | $0.638/hr | $0.766/hr |
| H100 80GB | $1.499/hr | $1.799/hr |
| H200 141GB | $2.249/hr | $2.699/hr |

## Provider Configuration

Current markup rates (configurable in `app_server.py`):

```python
PRICING_MARKUP = {
    "verda": 1.20,   # 20% markup
    "targon": 1.20,  # 20% markup
    "default": 1.20  # Default for any provider
}
```

## Billing

- All prices are per-hour
- Spot instances are billed in 1-second increments
- Minimum billing period: 1 minute
- Instances are billed from start until termination

## Questions?

Contact support for volume discounts or enterprise pricing.
