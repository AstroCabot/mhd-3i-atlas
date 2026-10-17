// Colour roles shared by chart creation and updates to an existing chart.
const legacyRoles = {
  '#c5a369':'argon', '#85a9c4':'codex', '#d47d75':'claude',
  '#b5afa3':'chart-text', '#a39b8c':'chart-text', '#afa697':'chart-text',
  '#7b8f9e':'chart-text', '#91a1ae':'chart-text', '#24211c':'tooltip-bg',
  '#514a3e':'chart-axis', '#eae5da':'text', '#3b362e':'chart-grid',
  '#25343f':'line', '#191713':'panel', '#687d8d':'chart-handle',
  '#a99b7d':'chart-window-label', '#d4dee5':'observed', '#cad6df':'observed',
  '#b4c3cf':'observed', '#81919e':'comparator', '#8d9fab':'comparator',
  '#b4f57a':'argon',
};
const roles = [...new Set(Object.values(legacyRoles))];
export function readPalette() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(roles.map(role => [role, style.getPropertyValue(`--${role}`).trim()]));
}
function replaceColors(value, replacements, palette) {
  if (typeof value === 'string') {
    const variable = /^var\(--([\w-]+)\)$/.exec(value);
    if (variable && palette[variable[1]]) return palette[variable[1]];
    const hex = /^(#[\da-f]{6})([\da-f]{2})?$/i.exec(value);
    if (hex && replacements[hex[1].toLowerCase()]) return replacements[hex[1].toLowerCase()] + (hex[2] || '');
    return value;
  }
  if (Array.isArray(value)) return value.map(item => replaceColors(item, replacements, palette));
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.entries(value).map(([key,item]) => [key,replaceColors(item,replacements,palette)]));
  }
  return value;
}
export function chartColors(option, previousPalette) {
  const palette = readPalette();
  const replacements = previousPalette
    ? Object.fromEntries(Object.entries(previousPalette).map(([role,color]) => [color.toLowerCase(),palette[role]]))
    : Object.fromEntries(Object.entries(legacyRoles).map(([color,role]) => [color,palette[role]]));
  return replaceColors(option,replacements,palette);
}
export function chartColor(color) { return chartColors(color); }
