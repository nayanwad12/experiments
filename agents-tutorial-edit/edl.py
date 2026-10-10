"""Edit decision list. Each kept range is (first word start, last word start) in source seconds;
build.py pads to the real word edges. ("raw", s, e) keeps a span untouched (no pause trimming):
used for the finished reel playing back, which has its own music and timing."""

PARTS = [
    ("01", "Introduction - What the Agent Skills Can Do", [
        (0.98, 25.08),      # tutorial overview + the 9 video types
        # cut: "so I just want to show the tutorial first and this is the video" (repeat)
        (30.72, 36.79),     # "this is the video ... the AI edited it for me"
        (38.71, 42.64),     # comparison video
        (44.95, 46.18),     # also a comparison video
        (48.81, 56.09),     # launch video + what we'll learn
        # cut: "So what you have to do is you just have" (false start)
        (60.73, 69.12),     # agents + combined markdown file
        # cut: OBS pause + "Thank you" (ASR noise)
        (77.30, 79.79),     # "which I explained in the previous lectures"
    ]),
    ("02", "Installing the Vibe Editing System Skill", [
        (82.17, 85.19, 85.62),  # "so now we are going to use these nine skills" (end before stray syllable)
        # cut: "this one two three seven eight" (miscount)
        (89.93, 92.65),     # "one ... nine, these are the nine skills"
        (94.86, 97.03),     # click on this
        # cut: "and you just have to download it" (said twice)
        (101.96, 102.76),   # click on download
        (104.37, 106.06),   # opens a drive link
        # cut: "and you're going to get this video downloaded"
        (109.10, 119.96),   # open Claude Code, paste the skill, "install this skill for me"
        (120.93, 121.45),   # "so this is a skill"
        # cut: "which is which has every set of instructions ... so" (restart)
        (127.09, 130.38),   # "which has every set of instruction ..."
        (131.88, 141.02),   # start here
    ]),
    ("03", "Editing a Talking-Head Video", [
        # cut: first "and suppose you want to create a video like this" (said twice)
        (145.98, 147.20),
        (148.88, 149.57),   # it's a talking head video
        (151.10, 154.35),   # install this skill
        (156.67, 158.45),   # click send
        (160.10, 164.33),   # download the talking head skill
        # cut: 15 s of silent navigation
        (179.91, 180.65),   # click here
        (182.65, 183.71),   # on the talking head one
        # cut: "format"
        (188.34, 189.31),   # download this
        (191.08, 202.38),   # download the complete folder as zip, paste it here
        # cut: "this is" (false start)
        (203.68, 209.05),   # this skill is already installed ... install this talking head
        (211.37, 220.23),   # install this skill as well ... click enter
        # cut: "so this is the starting point and" (said 3 times, kept once)
        (228.35, 234.58),   # starting point, playbook for 8 video types
        # cut: "So this is the starting point and this is the 8 video formats which you can use and"
        (246.68, 254.28),   # upload your video, let me find one
        # cut: "so let me just" + OBS pause
        (264.94, 267.20),   # video file I'm going to attach
        (269.92, 273.61),   # this is my video (raw clip plays, stop before "right now")
        # cut: "So this is the video I have attached" (repeat), "We just have to describe" (restart)
        (280.34, 287.73),   # describe in plain words, let me type that
        # cut: OBS pause while typing
        (291.09, 298.57),   # kinetic captions, white and blue
        # cut: OBS pause, "have to write like"
        (305.01, 307.29),   # behind captions
        (309.91, 319.59),   # motion graphics, music, SFX, ending card with the message
        # cut: "with the message" (repeat)
        (323.93, 327.07),   # join vibe editing + paper cut animation
        (327.99, 328.80),   # so what is the process
        # cut: "this is the process" (repeat)
        (331.28, 341.15),   # installed this skill first, then the second skill
        # cut: "if you" (stutter)
        (342.31, 348.56),   # skip talking head if you don't need it
        (349.91, 354.58),   # click enter, it starts editing
        # cut: 12 s silent
        (366.61, 389.10),   # same process for motion graphics; the system by Ideabro Studios; 8 skills
        # cut: "so this is the new set of tutorial" (restart)
        (392.45, 397.42),   # new module in this course
        # cut: ASR noise "*Dramatic music"
        (399.83, 401.06),   # it has started the editing
        # cut: "and I am just going to show"
        (403.78, 416.68),   # iterations: just type in the chat box
        # cut: 9 s silent
        (425.90, 433.87),   # it takes 12-15 minutes
    ]),
    ("04", "Creating a Launch Ad and Combining Skills", [
        (436.35, 436.57),   # so similarly
        # cut: "you" (stutter)
        (437.53, 439.98),   # launch video: click on this
        (442.34, 442.91),   # and you just have to download
        # cut: "let me create another" (said twice)
        (453.07, 455.54),   # let me create another Claude project
        # cut: "let me create this" + silent wait
        (470.10, 472.01),   # install this skill for me
        (474.30, 483.77),   # first skill already installed; install the skill per video type
        # cut: "I hope this will help this"
        (489.51, 493.72),   # already described in the library / prompting guide
        (494.64, 495.90),   # but since I'm recording this video tutorial
        # cut: "so if"
        (496.73, 499.28),   # you will get an idea how to actually do this
        (501.72, 507.07),   # installing the launch videos skill
        # cut: "So I'm going to create a launch video for" (restart)
        (514.54, 518.06),   # launch video for H&M
        # cut: silent Google search
        (527.28, 529.31),   # click the link of H&M
        # cut: muttering while typing (unclear audio), "this is the link I've already installed"
        (543.87, 544.94),   # this is the link which we have to paste
        # cut: muttering while typing
        (563.70, 568.88),   # write in your layman language
        # cut: "so and also add"
        (575.04, 577.40),   # add big kinetic captions
        (581.36, 582.42),   # follow the theme of the website
        # cut: "so I just wrote this and" / "interactive" / "Punch" (typing mutters)
        (602.48, 603.30),   # So I just wrote this
        (603.93, 611.30),   # upload your design system for specific colours
        (611.79, 614.96),   # skill already installed, this is enough
        # cut: "thing so this is enough" (repeat)
        (617.45, 619.10),   # it has all the instructions
        (619.90, 621.68),   # click on send
        # cut: "so this is our project going"
        (626.18, 637.62),   # Vibe Launch Ads skill by Ideabro Studios is creating it
        (640.15, 640.97),   # so if you want to be specific
        # cut: "if you want to like create 16:9 launch" (restart)
        (645.18, 648.18),   # like 16:9 aspect ratio, just specify
        (649.32, 651.91),   # otherwise it picks one
        (652.03, 654.82),   # add more and more instructions
        (655.57, 657.45),   # write in layman language
        # cut: "and there's no need to like make certain things in"
        (663.62, 665.72),   # you don't have to generate a prompt
        # cut: "because skills has already things"
        (671.33, 674.72),   # tools built for our students
        # cut: "So it is running the system and" + OBS + "Let me just check. Yes"
        (686.90, 689.02),   # wait ~15 minutes
        (691.54, 698.10),   # depends on duration and animations
        # cut: "so similarly similarly we can use this motion graphics" (restart)
        (707.80, 713.33),   # motion graphics / animations
        (714.35, 718.91),   # sound effects
        # cut: "so you can even you can use a thumb combination of this" (restart)
        (723.94, 741.84),   # combine skills or use standalone; install the system first
    ]),
    ("05", "The Results and Blocked Websites", [
        # cut: "So" "since"
        (747.23, 751.37),   # let me cut to the part where things are done
        # cut: "so it will take around 12 to 15 minutes" (already said) + OBS pause
        (759.25, 763.70),   # it has done the editing
        (765.27, 767.02),   # this is the edit it has given me
        # cut: "so I'm talking about the" + first playback start that was restarted
        ("raw", 774.95, 786.00),   # the finished reel plays
        # cut: "so it is just loading"
        ("raw", 788.62, 814.60),   # reel continues to end card
        # cut: mutters "I did everything"
        (820.15, 825.48),   # this is the output, the magic of our skill
        (827.51, 828.92),   # this is the skill I'm talking about
        # cut: "Hacked. so much of things to do."
        (833.59, 845.33),   # any type of editing; reuse as template
        # cut: OBS pause
        (848.71, 849.35),   # also there is one thing
        (851.31, 854.63),   # launch video of H&M
        # cut: "because H&M has blocked there" (restart)
        (858.04, 865.05),   # Claude can't access H&M: they block third-party agents
        # cut: "so I just so since we can't do this"
        (868.92, 877.55),   # Snitch allows access, H&M blocks it
        # cut: "so I just uploaded the individual cut of the photo" (restart)
        (882.28, 885.41),   # uploaded group of photos, it makes cutouts
        # cut: "so since it has now started again the things"
        (893.50, 898.81),   # now it is creating a launch video for us
        # cut: same reel played a second time (shown above), "this is the similar procedure",
        #      second explanation of the H&M block (already covered)
        (968.10, 970.12),   # if it's not available then you just have to
        # cut: "take a screenshot and" (repeat)
        (972.15, 974.59),   # take a screenshot of the cutout of whatever you want
        # cut: "to be in whatever you including the video and like this like this you have to work"
        (980.45, 983.89),   # so yeah this is the main tutorial and I'm also going to share the
        (989.01, 990.87),   # H&M launch video in the next part
        # cut: "so just stay" (cut off by end of recording) + OBS
    ]),
]
