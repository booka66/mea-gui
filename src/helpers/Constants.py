from PyQt5.QtGui import QColor

VERSION = "v0.0.2"

# Maybe use Gruvbox color:
# color_fg0 = '#fbf1c7'
# color_bg1 = '#3c3836'
# color_bg3 = '#665c54'
# color_blue = '#458588'
# color_aqua = '#689d6a'
# color_green = '#98971a'
# color_orange = '#d65d0e'
# color_purple = '#b16286'
# color_red = '#cc241d'
# color_yellow = '#d79921'

BACKGROUND = QColor("#4a4e69")
ACTIVE = QColor("#808080")
SEIZURE = QColor("#0096c7")
SE = QColor("#ffb703")
PROPAGATION = QColor("#a8dadc")

HOVER = QColor("#00ff00")
SELECTED = QColor("#008000")
PLOTTED = QColor("#ef233c")

SIZE = 30
MARKER = "s"

STROKE_WIDTH = 3

GRAPH_DOWNSAMPLE = 5_000

TOTAL_POINTS = 20_000

CELL_SIZE = 60  # micrometers

MAC = "darwin"
WIN = "win32"

# Font-specific constants
FONT_FILE = "GeistMonoNerdFontMono-Regular.otf"
FONT_FAMILY = "GeistMono Nerd Font Mono"
SCREEN_DIAGONLA_THRESHOLD = 13
SMALL_FONT_SIZE = 8
LARGE_FONT_SIZE = 12
