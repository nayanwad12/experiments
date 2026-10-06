VOICE = "am_michael*0.5+am_onyx*0.5"         # documentary narrator
NARR = "af_heart*0.6+af_bella*0.4"           # the page's voice (tail)
LINES = [
    ("hook", "In 1996, one number destroyed a rocket in under forty seconds.", None, 1.0,
     "In nineteen ninety-six, one number destroyed a rocket in under forty seconds."),
    ("lift", "June 4th. Ariane 5 lifts off on its very first flight.", None, 1.0,
     "June fourth. Ariane five lifts off on its very first flight."),
    ("inside", "Inside its guidance computer, a piece of old code...", None, 1.0),
    ("squeeze", "tries to squeeze a 64-bit number into 16 bits.", None, 1.0,
     "tries to squeeze a sixty-four bit number into sixteen bits."),
    ("max", "Sixteen bits can only hold up to 32,767.", None, 1.0,
     "Sixteen bits can only hold up to thirty-two thousand, seven hundred and sixty-seven."),
    ("over", "The rocket's sideways speed reading is bigger.", None, 1.0),
    ("overflow", "Overflow.", None, 0.9),
    ("crash", "The computer crashes. The backup runs the same code, and crashes too.", None, 1.02),
    ("veer", "The rocket swings sideways, and tears itself apart.", None, 1.0),
    ("lost", "Four satellites. Hundreds of millions of dollars. Lost to one conversion.", None, 0.98),
    ("tail", "This documentary has no stock footage and no AI video. Every frame is code, too.", NARR, 1.08),
    ("cta", "Follow for more stories like this.", NARR, 1.05),
]
