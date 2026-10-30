// Select only visible article-route diamonds; company anchors and empty space do not select.
export function markerAt(root, x, y, allowed) {
    let nearest = null
    let distance = 11
    for (const point of root.querySelectorAll('.scattergeo path.point')) {
        const group = point.closest('.trace.scattergeo')
        const rows = group?.__data__
        if (!Array.isArray(rows)) continue
        const index = rows.indexOf(point.__data__)
        const id = rows[0]?.trace?.customdata?.[index]
        if (!allowed.has(id)) continue
        const rect = point.getBoundingClientRect()
        if (!rect.width || !rect.height) continue
        const next = Math.hypot(x - (rect.left + rect.width / 2), y - (rect.top + rect.height / 2))
        if (next < distance) {
            nearest = id
            distance = next
        }
    }
    return nearest
}

export default function(component) {
    const {parentElement, data, setTriggerValue} = component
    const root = parentElement.host.closest('.st-key-rr_article_map_area')
    if (!root) return
    const allowed = new Set(data.ids)
    let start = null
    const down = event => {
        start = {x: event.clientX, y: event.clientY, button: event.button}
    }
    const up = event => {
        if (!start || start.button !== 0) return
        const moved = Math.hypot(start.x - event.clientX, start.y - event.clientY)
        start = null
        if (moved > 5) return
        const selected = markerAt(root, event.clientX, event.clientY, allowed)
        if (selected && selected !== data.focus) setTriggerValue('picked', selected)
    }
    root.addEventListener('pointerdown', down, true)
    root.addEventListener('pointerup', up, true)
    return () => {
        root.removeEventListener('pointerdown', down, true)
        root.removeEventListener('pointerup', up, true)
    }
}
