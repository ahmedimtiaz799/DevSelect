function markdownLinkToPlainText(_, label, destination) {
  const url = destination
    .trim()
    .replace(/\s+["'][^"']*["']\s*$/, '')

  if (!/^(?:https?:\/\/|mailto:)/i.test(url)) return label

  return label === url ? url : `${label} (${url})`
}

export function markdownToPlainText(markdown) {
  if (typeof markdown !== 'string') return ''

  return markdown
    .replace(/\r\n?/g, '\n')
    .replace(/```[^\n]*\n?([\s\S]*?)```/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\(((?:[^()]|\([^()]*\))*)\)/g, markdownLinkToPlainText)
    .replace(/<((?:https?:\/\/|mailto:)[^>]+)>/gi, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}>\s?/gm, '')
    .replace(/^(\s*)[-+*]\s+/gm, '$1• ')
    .replace(/(\*\*|__)([\s\S]*?)\1/g, '$2')
    .replace(/~~([\s\S]*?)~~/g, '$1')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/(\*|_)([^*_\n]+)\1/g, '$2')
    .replace(/^\s{0,3}(?:[-*_]\s*){3,}$/gm, '')
    .replace(/\\([\\`*_[\]{}()#+\-.!>])/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
