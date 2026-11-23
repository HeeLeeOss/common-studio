% Authored for Common Studio as a test fixture and released under the Unlicense.
\version "2.24.0"

\header {
  title = "Lantern Path"
  composer = "Common Studio fixture"
}

upper = \relative c'' {
  \clef treble \key g \major \time 6/8
  g8 a b d4 b8 | c4. ~ c8 b a | <g b>4. d4. |
  \repeat volta 2 { e8 fis g a4 fis8 } | g2. \bar "|."
}

lower = \relative c {
  \clef bass \key g \major \time 6/8
  g4. d' | a d | g, d' | c d | g,2.
}

\score {
  <<
    \new Staff = "upper" \upper
    \new Staff = "lower" \lower
  >>
  \layout { }
}
