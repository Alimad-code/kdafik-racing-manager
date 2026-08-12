const FALLBACK_READABLE_TEAM_ACCENT = "#9ca3af";
const MIN_READABLE_LUMINANCE = 0.28;
const MIN_READABLE_LIGHTNESS = 0.58;

function parseHexColor(color: string) {
  const value = color.trim();
  const match = /^#?([0-9a-f]{6})$/i.exec(value);

  if (!match) return null;

  const hex = match[1];
  return {
    r: Number.parseInt(hex.slice(0, 2), 16),
    g: Number.parseInt(hex.slice(2, 4), 16),
    b: Number.parseInt(hex.slice(4, 6), 16)
  };
}

function toHexChannel(value: number) {
  return Math.round(Math.max(0, Math.min(255, value)))
    .toString(16)
    .padStart(2, "0");
}

function rgbToHex(r: number, g: number, b: number) {
  return `#${toHexChannel(r)}${toHexChannel(g)}${toHexChannel(b)}`;
}

function getRelativeLuminance({ r, g, b }: { r: number; g: number; b: number }) {
  const [red, green, blue] = [r, g, b].map((channel) => {
    const value = channel / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function rgbToHsl({ r, g, b }: { r: number; g: number; b: number }) {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;

  if (max === min) {
    return { h: 0, s: 0, l: lightness };
  }

  const delta = max - min;
  const saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
  let hue = 0;

  if (max === red) {
    hue = (green - blue) / delta + (green < blue ? 6 : 0);
  } else if (max === green) {
    hue = (blue - red) / delta + 2;
  } else {
    hue = (red - green) / delta + 4;
  }

  return { h: hue / 6, s: saturation, l: lightness };
}

function hslToRgb({ h, s, l }: { h: number; s: number; l: number }) {
  if (s === 0) {
    const value = l * 255;
    return { r: value, g: value, b: value };
  }

  const hueToRgb = (p: number, q: number, t: number) => {
    let next = t;
    if (next < 0) next += 1;
    if (next > 1) next -= 1;
    if (next < 1 / 6) return p + (q - p) * 6 * next;
    if (next < 1 / 2) return q;
    if (next < 2 / 3) return p + (q - p) * (2 / 3 - next) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;

  return {
    r: hueToRgb(p, q, h + 1 / 3) * 255,
    g: hueToRgb(p, q, h) * 255,
    b: hueToRgb(p, q, h - 1 / 3) * 255
  };
}

export function getReadableTeamAccent(color: string | undefined | null) {
  if (!color) return FALLBACK_READABLE_TEAM_ACCENT;

  const rgb = parseHexColor(color);
  if (!rgb) return FALLBACK_READABLE_TEAM_ACCENT;

  if (getRelativeLuminance(rgb) >= MIN_READABLE_LUMINANCE) {
    return rgbToHex(rgb.r, rgb.g, rgb.b);
  }

  if (Math.max(rgb.r, rgb.g, rgb.b) <= 12) {
    return FALLBACK_READABLE_TEAM_ACCENT;
  }

  const hsl = rgbToHsl(rgb);
  const readableRgb = hslToRgb({
    ...hsl,
    l: Math.max(hsl.l, MIN_READABLE_LIGHTNESS)
  });

  return rgbToHex(readableRgb.r, readableRgb.g, readableRgb.b);
}
