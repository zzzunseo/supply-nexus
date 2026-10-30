import test from 'node:test'
import assert from 'node:assert/strict'
import bridge, {markerAt} from '../ui/article_route_click.mjs'

function fixture() {
    const row = {}
    const rows = [row]
    row.trace = {customdata: ['photoresist:jsr>tsmc']}
    const point = {
        __data__: row,
        closest: () => ({__data__: rows}),
        getBoundingClientRect: () => ({left: 100, top: 100, width: 8, height: 8})
    }
    const listeners = {}
    const root = {
        querySelectorAll: () => [point],
        addEventListener: (type, fn) => {listeners[type] = fn},
        removeEventListener: type => {delete listeners[type]}
    }
    return {root, point, listeners}
}

test('click uses the closest rendered marker and rejects empty space or unregistered IDs', () => {
    const {root} = fixture()
    assert.equal(markerAt(root, 104, 104, new Set(['photoresist:jsr>tsmc'])), 'photoresist:jsr>tsmc')
    assert.equal(markerAt(root, 130, 130, new Set(['photoresist:jsr>tsmc'])), null)
    assert.equal(markerAt(root, 104, 104, new Set(['unrelated'])), null)
})

test('hidden markers cannot select', () => {
    const {root, point} = fixture()
    point.getBoundingClientRect = () => ({width: 0, height: 0})
    assert.equal(markerAt(root, 104, 104, new Set(['photoresist:jsr>tsmc'])), null)
})

test('one click sends one trigger, drag sends none, cleanup removes handlers', () => {
    const {root, listeners} = fixture()
    const sent = []
    const cleanup = bridge({parentElement: {host: {closest: () => root}},
        data: {ids: ['photoresist:jsr>tsmc'], focus: null}, setTriggerValue: (...args) => sent.push(args)})
    listeners.pointerdown({clientX: 104, clientY: 104, button: 0})
    listeners.pointerup({clientX: 104, clientY: 104})
    assert.deepEqual(sent, [['picked', 'photoresist:jsr>tsmc']])
    listeners.pointerdown({clientX: 80, clientY: 104, button: 0})
    listeners.pointerup({clientX: 104, clientY: 104})
    assert.equal(sent.length, 1)
    cleanup()
    assert.equal(Object.keys(listeners).length, 0)
})

test('clicking the current focus does not cause another rerun', () => {
    const {root, listeners} = fixture()
    const sent = []
    bridge({parentElement: {host: {closest: () => root}},
        data: {ids: ['photoresist:jsr>tsmc'], focus: 'photoresist:jsr>tsmc'}, setTriggerValue: (...args) => sent.push(args)})
    listeners.pointerdown({clientX: 104, clientY: 104, button: 0})
    listeners.pointerup({clientX: 104, clientY: 104})
    assert.equal(sent.length, 0)
})
