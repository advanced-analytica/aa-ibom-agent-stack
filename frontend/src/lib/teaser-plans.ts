/**
 * Hardcoded teaser plans used as a fallback when the Stripe-driven
 * `/billing/plans` endpoint returns an empty list — so the marketing surface
 * stays consistent regardless of backend state.
 *
 * Shape mirrors the simplified one used by `<PricingTeaser />` on the landing
 * page. The full /pricing page maps these into its own card UI.
 *
 * Replace these copy strings via the i18n `marketing.pricing.plans.*` keys
 * once you localize for additional languages.
 */
import { ROUTES } from "@/lib/constants";

export interface TeaserPlan {
  name: string;
  /** Display price, currency-prefixed (e.g. "$0", "$29"). Leave empty for "Custom". */
  price: string;
  /** Cadence label shown next to price (e.g. "/ month", "/ user / month"). */
  cadence?: string;
  description: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
  badge?: string;
}

export const TEASER_PLANS: TeaserPlan[] = [
  {
    name: "Starter",
    price: "$0",
    cadence: "/ month",
    description: "For individuals exploring the product.",
    features: ["100 messages / day", "1 connected data source", "Community support"],
    cta: { label: "Start free", href: ROUTES.REGISTER },
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "/ user / month",
    description: "For small teams getting real work done.",
    features: [
      "Unlimited messages",
      "10 connected sources",
      "Email + chat support",
      "Workflow automations",
    ],
    cta: { label: "Start 14-day trial", href: ROUTES.REGISTER },
    featured: true,
    badge: "Most popular",
  },
  {
    name: "Business",
    price: "$99",
    cadence: "/ user / month",
    description: "For organisations rolling out across teams.",
    features: [
      "Everything in Pro",
      "SSO + audit log",
      "Role-based access control",
      "Dedicated success manager",
    ],
    cta: { label: "Talk to sales", href: ROUTES.CONTACT },
  },
];

export function getTeaserPlans(_locale: string): TeaserPlan[] {
  return TEASER_PLANS;
}
