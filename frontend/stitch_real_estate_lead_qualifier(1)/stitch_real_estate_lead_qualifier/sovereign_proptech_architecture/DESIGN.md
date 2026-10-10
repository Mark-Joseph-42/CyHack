---
name: Sovereign Proptech Architecture
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#424845'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#727975'
  outline-variant: '#c1c8c4'
  surface-tint: '#4a645b'
  primary: '#00130d'
  on-primary: '#ffffff'
  primary-container: '#0f2922'
  on-primary-container: '#769188'
  inverse-primary: '#b0cdc2'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#1d0a00'
  on-tertiary: '#ffffff'
  tertiary-container: '#3c1c00'
  on-tertiary-container: '#d37300'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cce9de'
  primary-fixed-dim: '#b0cdc2'
  on-primary-fixed: '#052019'
  on-primary-fixed-variant: '#324c44'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-hero:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  metric-xl:
    fontFamily: Hanken Grotesk
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.03em
  label-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

The design system embodies the high-stakes precision of elite real estate brokerage paired with machine-intelligence reliability. It serves top-tier managing brokers, luxury acquisition teams, and institutional real estate asset managers who require instantaneous lead intelligence without visual noise.

The aesthetic fuses Swiss typographic discipline with refined architectural minimalism and subtle tactile depth. Every element emphasizes trust, transactional value, and crisp legibility. Rather than generic corporate SaaS styling, the interface adopts high-contrast micro-borders, deep forest undertones, and warm metallic accents reminiscent of luxury portfolio dossiers. The emotional resonance is calm, authoritative, and decisively high-yield.

## Colors

The palette establishes transactional status at a glance:

- **Primary Deep Slate-Emerald (`#0F2922`)**: Anchors global navigation, primary command buttons, and core structural framework. Communicates stability and private-banking authority.
- **Secondary Jade / Active Emerald (`#10B981` / hover `#059669`)**: Reserved exclusively for validated high-intent AI lead scores, positive margin vectors, and confirmed pipeline movements.
- **Tertiary Champagne Amber (`#D97706` / light tint `#F59E0B`)**: Denotes luxury-tier tiering, active negotiations, escrow holds, and priority VIP flags.
- **Critical Discard / Redline (`#E11D48`)**: Strict signaling for disqualified inquiries, non-viable buyer caps, and system friction alerts.
- **Neutral Canvas & Surfaces**:
  - Global Canvas: Architectural off-white (`#F8FAFC`).
  - Container Surfaces: Pure crisp white (`#FFFFFF`).
  - Structural Borders: Ultra-clean slate line work (`#E2E8F0`).
  - Heavy Typography & Metrics: Deep slate black (`#0F172A`).
  - Muted Metadata: Mid-tone slate gray (`#64748B`).

## Typography

The typographic hierarchy prioritizes density, clear scanning, and quantitative certainty:

- **Hanken Grotesk** powers all primary displays, titles, and structural interfaces. Its crisp geometric architecture delivers Swiss readability across fast data parsing.
- **JetBrains Mono** is deployed for analytical data, valuation tickers, lead scores (e.g., `SCORE: 98.4`), phone validation tags, and currency indicators. This monospaced separation distinguishes live calculation outputs from qualitative broker notes.
- Use tabular numbers (`font-variant-numeric: tabular-nums`) across all financial tables, escrow milestones, and quantitative metrics to preserve vertical alignment.

## Layout & Spacing

The structural layout uses a responsive 12-column fluid grid built upon a modular 4px/8px coordinate baseline:

- **Desktop (1280px+)**: 12-column grid, `2.5rem` section margins, `1.5rem` gutters. The desktop workstation accommodates a persistent left navigation rail (`260px`), dynamic qualification feed (`420px`), and a fluid focal dossier view.
- **Tablet (768px – 1279px)**: 8-column layout with `1.5rem` margins and gutters. Side panels compress into slide-over drawers; lead queues expand full-width with stacked inspection cards.
- **Mobile (< 768px)**: Single-column vertical stream, `1rem` outer canvas padding. Data tables transition into swipeable qualification cards with pinned bottom action bars.
- Component padding strictly adheres to tokenized boundaries: `space-xs` and `space-sm` for badge interiors and metric chips; `space-md` and `space-lg` for card surfaces and form module partitions.

## Elevation & Depth

Visual hierarchy relies on crisp perimeter definition rather than exaggerated drop shadows. The design uses low-contrast architectural outlines backed by tinted ambient grounding:

- **Surface Base**: Crisp pure white (`#FFFFFF`) grounded with a 1px solid border (`#E2E8F0`).
- **Elevation Tier 1 (Cards, Feed Items)**: 1px outline in `#E2E8F0` coupled with a subtle ambient shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02)`.
- **Elevation Tier 2 (Hover States, Active Selection)**: Transition border to `#0F2922` or `#10B981` (dependent on qualification state) accompanied by `0 4px 6px -1px rgba(15, 41, 34, 0.07), 0 2px 4px -2px rgba(15, 41, 34, 0.05)`.
- **Elevation Tier 3 (Modals, Overlays, Command Center)**: 1px border in `#CBD5E1` with a deep architectural veil: `0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.08)`.
- Backdrop filters on flyouts and floating bars utilize a frosted blur (`backdrop-blur-md` with `rgba(255, 255, 255, 0.85)`).

## Shapes

The design system maintains a refined, tailored shape language (`roundedness: 1`):

- **Default UI Containers & Cards**: Set to `0.375rem` (6px) or `0.5rem` (8px). Corners stay sharp enough to feel structured and institutional, avoiding bubbly casualness.
- **Input Fields & Action Controls**: `0.375rem` for compact precision.
- **Intent Badges & System Chips**: As an intentional exception, all status tags, confidence levels, and AI prediction markers utilize full pill rounds (`9999px`) to create immediate visual distinction against squared data tables and structural card containers.

## Components

### Buttons
- **Primary Command**: Background `#0F2922`, text `#FFFFFF`, border 1px solid `#0F2922`. Hover: `#163C32`. Active click states sink 1px.
- **High-Value AI Action**: Background `#10B981`, text `#FFFFFF`. Hover: `#059669`.
- **Secondary / Ghost**: Background `#FFFFFF`, text `#0F172A`, border 1px solid `#E2E8F0`. Hover: background `#F8FAFC`, border `#CBD5E1`.
- **Destructive Discard**: Background transparent, text `#E11D48`, border 1px solid `#FECDD3`. Hover: background `#FFF1F2`.

### Chips & Pill Badges
- **Lead Qualified (Tier 1)**: Emerald pill (`bg-[#ECFDF5]`, `text-[#065F46]`, `border-[#A7F3D0]`). Icon: checkmark or spark.
- **Negotiation / Escrow**: Amber pill (`bg-[#FFFBEB]`, `text-[#92400E]`, `border-[#FDE68A]`).
- **Disqualified / Cold**: Crimson pill (`bg-[#FFF1F2]`, `text-[#9F1239]`, `border-[#FECDD3]`).
- **Typography inside Chips**: JetBrains Mono `label-mono-sm` in all-caps tracking (`SCORE 94`, `PRE-APPROVED`, `UNQUALIFIED`).

### Cards & Dossiers
- Built on `#FFFFFF` with 1px border `#E2E8F0`. 
- Padding: `1.5rem` desktop, `1rem` mobile.
- Headers separate from content bodies using subtle hairline dividers (`border-b border-slate-100`).
- Priority cards include a left accent border strip (3px wide in `#10B981` or `#D97706`).

### Input Fields & Controls
- **Inputs**: Height `40px`, padding `0.5rem 0.75rem`, background `#FFFFFF`, border 1px solid `#CBD5E1`. Focused state: border `#0F2922`, ring `2px solid rgba(15, 41, 34, 0.15)`.
- **Checkboxes & Radios**: 16px squared (`rounded: 3px`) or circular controls. Active checked state fills `#0F2922` with a pure white checkmark.

### Domain-Specific Components
- **AI Score Gauge**: A circular or horizontal split meter rendering confidence scores (`0-100`) accompanied by predictive rationale tokens (e.g., `+34% Liquid Assets Verified`).
- **Lead Valuation Stream**: High-density row component displaying contact metadata, target acquisition window, budget bracket, and instant qualification trigger buttons.