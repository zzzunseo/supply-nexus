import test from 'node:test'
import assert from 'node:assert/strict'
import bridge, {markerAt} from '../ui/globe_click.mjs'

function fixture() {
    const row = {}
    const rows = [row]
    row.trace = {customdata: ['samsung']}
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
    assert.equal(markerAt(root, 104, 104, new Set(['samsung'])), 'samsung')
    assert.equal(markerAt(root, 130, 130, new Set(['samsung'])), null)
    assert.equal(markerAt(root, 104, 104, new Set(['tsmc'])), null)
})

test('hidden markers cannot select', () => {
    const {root, point} = fixture()
    point.getBoundingClientRect = () => ({width: 0, height: 0})
    assert.equal(markerAt(root, 104, 104, new Set(['samsung'])), null)
})

test('one click sends one trigger, drag sends none, cleanup removes handlers', () => {
    const {root, listeners} = fixture()
    const sent = []
    const cleanup = bridge({parentElement: {host: {closest: () => root}},
        data: {ids: ['samsung'], focus: null}, setTriggerValue: (...args) => sent.push(args)})
    listeners.pointerdown({clientX: 104, clientY: 104, button: 0})
    listeners.pointerup({clientX: 104, clientY: 104})
    assert.deepEqual(sent, [['picked', 'samsung']])
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
        data: {ids: ['samsung'], focus: 'samsung'}, setTriggerValue: (...args) => sent.push(args)})
    listeners.pointerdown({clientX: 104, clientY: 104, button: 0})
    listeners.pointerup({clientX: 104, clientY: 104})
    assert.equal(sent.length, 0)
})
