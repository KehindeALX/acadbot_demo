---
name: MSA AcadBot
description: Career-path learning platform for More Success Academy — navy-night surfaces, gilded accents, warm and ambitious.
colors:
  midnight: "#050B2E"
  midnight-deep: "#0A1445"
  midnight-lifted: "#111A5A"
  gilded: "#D4AF37"
  gilded-bright: "#F0D060"
  gilded-tint: "rgba(212, 175, 55, 0.15)"
  lagoon: "#00C9B1"
  lagoon-tint: "rgba(0, 201, 177, 0.15)"
  white: "#FFFFFF"
  muted: "#8A94B2"
  border: "#1E2A5A"
  red: "#FF6B6B"
  green: "#4CAF50"
typography:
  display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "clamp(28px, 5vw, 44px)"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "clamp(22px, 4vw, 32px)"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "clamp(18px, 3vw, 24px)"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Inter, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
  xl: "18px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
components:
  button-primary:
    backgroundColor: "{colors.gilded}"
    textColor: "{colors.midnight}"
    rounded: "{rounded.md}"
    padding: "8px 24px"
  button-primary-hover:
    backgroundColor: "{colors.gilded-bright}"
  button-secondary:
    backgroundColor: "{colors.midnight}"
    textColor: "{colors.gilded}"
    rounded: "{rounded.md}"
    padding: "8px 24px"
  button-ghost:
    backgroundColor: "{colors.midnight}"
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    padding: "8px 24px"
  card:
    backgroundColor: "{colors.midnight-deep}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input:
    backgroundColor: "{colors.midnight}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  navbar-link:
    backgroundColor: "{colors.midnight}"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "4px 16px"
  badge-published:
    backgroundColor: "{colors.gilded-tint}"
    textColor: "{colors.gilded}"
    rounded: "{rounded.pill}"
    padding: "4px 8px"
---

# Design System: MSA AcadBot

## Overview

**Creative North Star: "The Gold-Standard Academy"**

MSA AcadBot is a gold-standard academy at midnight: deep navy surfaces hold the authority and calm of a prestigious institution, while warm gilded gold — the accent for every action — carries the promise of achievement. The voice is warm and ambitious, not cold and corporate: it should feel like a confident, encouraging mentor standing beside a student working toward their career, with AI assistance (the "bot") as the co-pilot.

Density is moderate and calm — generous 24px card padding, comfortable type, nothing crowded. Headlines set in the geometric warmth of Space Grotesk; body copy in the quiet readability of Inter. Depth is conveyed through layered navy surfaces (page → card → lifted accent) and soft, restrained shadows that appear only when a card lifts on hover. The interface stays consistent across pages: the same nav bar, the same card grammar, the same gold-voiced action buttons, so a student never re-learns a pattern from courses to dashboard.

**Key Characteristics:**
- Midnight-navy layered surfaces with gold as the singular action voice.
- Warm, mentor-toned copy and an aspirational, achievement-forward mood.
- Geometric display type (Space Grotesk) over quiet body type (Inter).
- Flat at rest, gently lifted on hover — depth is earned, not constant.
- One consistent component grammar across every page.

## Colors

The palette is a nocturnal prestige scheme: three deep navy grounds, a metallic gold accent, and a fresh lagoon teal that adds life without competing with gold.

### Primary
- **Gilded Gold** (#D4AF37): The action voice. Used for primary buttons, the active nav state, progress bars, focus outlines, and the brand mark. On hover it brightens to Gilded Bright (#F0D060). Gold is warm against the navy and reads as "do this / you're progressing."
- **Gilded Bright** (#F0D060): Hover/lit state of Gilded Gold — a brighter, more energetic gold for interactive lift.

### Secondary
- **Lagoon Teal** (#00C9B1): The guidance voice. Used for links, success/active status, and informational accents. Teal complements gold (complementary on the wheel) without competing — it signals "here's more / healthy state," while gold signals "act."
- **Lagoon Tint** (rgba(0, 201, 177, 0.15)): Soft teal wash for badge backgrounds.

### Neutral
- **Midnight Navy** (#050B2E): The page ground — the night sky everything sits on.
- **Midnight Deep** (#0A1445): Card surfaces, one step up from the ground.
- **Midnight Lifted** (#111A5A): Elevated fills (thumbnails, placeholder bands).
- **White** (#FFFFFF): Primary text on navy; headings.
- **Muted** (#8A94B2): Secondary/tertiary text, placeholders, inactive labels.
- **Border** (#1E2A5A): Hairline borders between layers and inside cards.
- **Red** (#FF6B6B): Errors and destructive actions.
- **Green** (#4CAF50): Success states (with Lagoon for active/completed status where warmth suits).

### Named Rules
**The Gold-Voice Rule.** Gold is the singular voice of action and progress — buttons, active nav, focus, progress. Everything else recedes to navy and muted. When two elements compete for gold, one must be demoted to teal or ghost.

**The Night-Ground Rule.** Midnight Navy is the literal ground of every screen. No surface goes darker than the page; cards lift *up* from it in Midnight Deep, never darker.

## Typography

**Display Font:** Space Grotesk (with sans-serif fallback)
**Body Font:** Inter (with sans-serif fallback)

**Character:** Space Grotesk brings a confident, slightly technical-but-warm geometric voice — right for an ambitious academy with an AI bent. Inter carries the body with calm neutrality, letting the display type lead while never fighting it.

### Hierarchy
- **Display** (700, clamp(28px, 5vw, 44px), 1.2): Page-level headlines — the strongest statement on the screen.
- **Headline** (700, clamp(22px, 4vw, 32px), 1.2): Section headings.
- **Title** (700, clamp(18px, 3vw, 24px), 1.2): Card titles — course names, lesson titles.
- **Body** (400, 15px, 1.65): Descriptive copy, set in Muted on navy for secondary emphasis.
- **Label** (600, 13px, 1.5): Form labels, small UI text, badges (which add uppercase + 0.5px letter-spacing at 11px).

### Named Rules
**The Two-Face Rule.** Space Grotesk owns every heading; Inter owns every body, label, input, and button label. A heading is never set in Inter and body copy is never set in Space Grotesk.

## Layout

The system uses a CSS grid with a 24px gutter, stacking to a single column on mobile. Grid columns collapse progressively at 1024px (tablets) and 640px (mobile), where grids drop to one column and page/nav padding tightens to 16px. Auto-fill grids use `minmax(280px, 1fr)` so cards keep a comfortable minimum width.

Spacing follows a strict 4-point rhythm: 4 / 8 / 16 / 24 / 32 / 48px. Card bodies and the space between cards sit at 24px; tight internal groupings (icon-to-label, badge padding) sit at 4–8px. A sticky top nav with backdrop blur keeps the brand and primary navigation in reach while scrolling.

## Elevation & Depth

The system is **layered, not shadow-driven.** Depth comes primarily from stacking navy surfaces (page → Midnight Deep cards → Midnight Lifted fills), with shadows used sparingly to signal interactivity. At rest, cards are flat — only a 1px Border hairline separates them from the page. On hover, a card lifts with a slight translateY and gains a soft shadow, making it feel tappable.

### Shadow Vocabulary
- **Ambient** (`0 2px 8px rgba(0,0,0,0.2)`): Small lift, minor interactive elements.
- **Raised** (`0 6px 20px rgba(0,0,0,0.3)`): Standard card hover lift.
- **Floating** (`0 12px 40px rgba(0,0,0,0.4)`): Course cards on hover and toasts — the highest interactive elevation.

### Named Rules
**The Lift-on-Hover Rule.** Surfaces are flat at rest with only a border. Elevation (shadow + translateY) appears only as a response to hover — an invitation to click. No resting card casts a shadow.

## Shapes

The form language is **softly rounded, approachable.** Cards and large surfaces use a 14px radius; buttons and form fields use 10px; and pills (999px) handle badges, nav links, and progress bars. This gives the academy a friendly, modern feel — precise but never sharp or corporate. Buttons, inputs, and cards all share the rounded family so the system reads as one coherent shape language. Focus states render as a 2px Gilded Gold outline with a 2px offset on `:focus-visible`.

## Components

### Buttons
- **Shape:** Rounded (10px); small buttons at 12px, standard at 14px, large at 16px, full-width via `--block`.
- **Primary (Gilded Gold):** Gold fill, Midnight Navy text, 8px × 24px padding. Hover brightens to Gilded Bright. This is the default CTA for enroll, continue, submit.
- **Secondary (Outlined Gold):** Transparent fill, Gold border + text; hover washes in Gold Tint. Used for career filters and paired secondary actions.
- **Ghost (Outlined Border):** Transparent, Muted text, Border hairline; hover borders gold. Low-emphasis tertiary actions.
- **Danger / Success:** Red / Green fills for destructive and positive confirmations.
- **Disabled:** 50% opacity, `not-allowed` cursor.

### Chips / Badges
- **Style:** Pill (999px), 11px uppercase with 0.5px letter-spacing, 4px × 8px padding, tinted background + 1px border.
- **States:** Published (Gold Tint/Gold), Draft (Muted Tint/Muted), Active (Green Tint/Green), Completed (Lagoon Tint/Lagoon).

### Cards / Containers
- **Corner Style:** Rounded (14px).
- **Background:** Midnight Deep (#0A1445) over the Midnight Navy page.
- **Shadow Strategy:** Flat at rest (see The Lift-on-Hover Rule); 1px Border hairline always separates surface from page.
- **Internal Padding:** 24px body.

### Inputs / Fields
- **Style:** Midnight Navy fill, 1px Border hairline, 10px radius, 8px × 16px padding, white text.
- **Focus:** Border shifts to Gilded Gold with a 3px Gold Tint ring (`0 0 0 3px`).
- **Error / Disabled:** Field errors in Red below the field; disabled at 60% opacity.

### Navigation
- **Style:** Sticky bar with 10px backdrop blur, 1px bottom Border, 16px × 32px padding.
- **Logo:** Brand mark in Gilded Gold (Space Grotesk 700, 18px) with a white wordmark; a text placeholder stands in for the real logo today.
- **Links:** Pill buttons (4px × 16px), Muted text, Border hairline; hover + focus border and text shift to Gold; active state fills Gold with Midnight Navy text.
- **Mobile:** Padding tightens to 16px; the primary action ("Sign In"/"Sign Up") stays visible.

### Progress Bar
- **Style:** 8px pill track in Border; the fill is a gold gradient (Gilded → Gilded Bright) that animates width at 0.3s.

### Toast
- **Style:** Midnight Deep card with a 1px status-colored border (Green/Red/Teal), 16px × 24px padding, Floating shadow, slide-in from the right; fixed bottom-right, stacked.

## Do's and Don'ts

### Do:
- **Do** keep gold for action and progress; demote competing accents to teal or ghost.
- **Do** use the 4-point spacing rhythm (4/8/16/24/32/48) so every screen breathes consistently.
- **Do** set every heading in Space Grotesk and every body/label in Inter.
- **Do** keep cards flat at rest and lift them only on hover.
- **Do** write labels, errors, and empty states in a warm, mentor-like voice — aspirational, never scolding.
- **Do** keep one shared component grammar across courses, course-detail, and dashboard.

### Don't:
- **Don't** add a surface darker than Midnight Navy — the page is the ground.
- **Don't** render primary buttons in teal or secondary buttons in gold; roles stay fixed.
- **Don't** invent a logo — the styled-text placeholder stands in until a real logo is supplied.
- **Don't** introduce a new radius outside the 6/10/14/18/pill family.
- **Don't** cast a resting shadow on any card; shadows are reserved for interaction.
- **Don't** use color alone to convey meaning without supporting text or icons (e.g. badge text always accompanies the tint).
