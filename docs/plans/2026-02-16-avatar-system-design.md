# User Profile Avatar System — Design Document

**Date**: 2026-02-16
**Status**: Approved
**Approach**: Unified Avatar Resolution (frontend-driven fallback)

## Goal

Users can upload and manage a custom profile avatar. When no custom avatar exists, a deterministic fallback chain provides a consistent image across all sessions and views.

## Decisions

| Decision | Choice |
|----------|--------|
| Storage | Cloudflare R2 (S3-compatible, no egress fees) |
| Image Processing | Backend (Pillow) — resize, crop, compress |
| Output Format | WebP, 256x256, quality 85 |
| Fallback Style | Initials on deterministic colored background (inline SVG) |
| Fallback Location | Frontend component (display concern) |
| Max Upload Size | 5MB raw |
| Accepted Types | image/jpeg, image/png, image/webp |

---

## 1. Schema Changes

Both `User` (OAuth) and `CredentialUser` (credentials) tables get two new nullable columns:

| Column | Type | Purpose |
|--------|------|---------|
| `avatar_url` | `String(512)` | URL to custom-uploaded image in R2 |
| `oauth_avatar_url` | `String(512)` | Captured from OAuth provider at login |

OAuth provider image is persisted to `oauth_avatar_url` at each sign-in (kept fresh). Credential users have `oauth_avatar_url = null` always.

NextAuth JWT callback is augmented to include `avatarUrl` and `oauthAvatarUrl` in the session object.

## 2. Upload API & Image Processing

### `POST /api/v1/users/me/avatar`

- Accepts `multipart/form-data` with single image file
- Validation:
  - MIME type whitelist: `image/jpeg`, `image/png`, `image/webp`
  - Magic byte verification (don't trust Content-Type alone)
  - Max file size: 5MB
- Processing (Pillow):
  - Center-crop to square
  - Resize to 256x256
  - Convert to WebP at quality 85 (~10-30KB output)
- Storage:
  - R2 path: `avatars/{user_id}.webp`
  - Overwrites on re-upload (no orphaned files)
  - Filename always derived from user ID (user's original filename ignored)
- Updates `avatar_url` on user record
- Returns new URL

### `DELETE /api/v1/users/me/avatar`

- Deletes object from R2
- Sets `avatar_url = null`
- Frontend falls back to next tier automatically

Both endpoints require valid session (X-User-Id header).

## 3. Frontend Avatar Component

### `<Avatar>` Component

Shared across all views: navbar, settings, dashboard, comments.

**Props:**
- `name: string` — user display name
- `avatarUrl?: string` — custom upload URL
- `oauthAvatarUrl?: string` — OAuth provider URL
- `size: "sm" | "md" | "lg"` — 24px / 32px / 48px

### Fallback Chain (deterministic, in order)

1. **Custom upload** (`avatarUrl`) — `<img>` tag
2. **OAuth provider image** (`oauthAvatarUrl`) — `<img>` tag
3. **Generated initials** — inline SVG, no network call
4. **Default icon** — neutral "?" circle (unreachable in practice)

### Generated Initials Logic

- Extract 1-2 initials from name ("Brandon Lee" → "BL")
- Hash name/email to index into fixed palette of 8-10 dark-theme colors
- Render as inline SVG: colored circle + white text
- Pure function — SSR-safe, deterministic, no randomness

### Error Handling

- `<img onError>` falls through to next tier (broken R2 URL → try OAuth URL → generated SVG)
- React state tracks active tier
- Fixed `width`/`height` attributes prevent layout shift

### Integration Points

- `nav.tsx` — replace text-only user display
- `account-section.tsx` — replace conditional `<img>`, add upload/remove buttons
- Future profile or comment views

## 4. Security

- MIME type validation + magic byte check
- Filename sanitization (always `{user_id}.webp`)
- 5MB upload limit
- No user-controlled paths in storage keys

## 5. Performance

- WebP output at 256x256 = ~10-30KB per avatar
- R2 serves via CDN (custom domain or `.r2.dev`)
- Generated fallback is inline SVG (zero network overhead)
- Fixed dimensions prevent CLS (Cumulative Layout Shift)
