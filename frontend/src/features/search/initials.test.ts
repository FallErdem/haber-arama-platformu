import { describe, expect, it } from 'vitest'
import { initialsOf } from './initials'

describe('initialsOf', () => {
  it.each([
    ['iki kelime', 'TRT Haber', 'TH'],
    ['tek kelime', 'NTV', 'NT'],
    ['ikiden fazla kelime', 'The New York Times', 'TN'],
    ['küçük harfle başlayan kelime (Türkçe büyük İ)', 'ileri haber', 'İH'],
    ['fazla boşluk', '  Global   Voices ', 'GV'],
  ])('%s', (_case, name, expected) => {
    expect(initialsOf(name)).toBe(expected)
  })
})
