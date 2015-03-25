#!/usr/bin/env python
import common

m = common.mongo()
installs = m['installs']

data = [
(1, 'avizha2@uic.edu', '06221f563bfb45fe87d9efc86aff4950',),
(1, 'Avizha2@uic.edu', '06221f563bfb45fe87d9efc86aff4950',),
(1, 'avizha2@uic.edu', 'be0a9cc315f7413c9378814b5d978589',),
(1, 'avizha2@uic.edu', 'de4bbd85c6b54a07944e5489244f716b',),
(1, 'djmccart@gmail.com', '504281f191b9403ba80c48fa71bdcb8e',),
(1, 'dmccart@gmail.com', 'd379ac29e9d7407f80e2ad3241507aa7',),
(1, 'dmccart@uic.edu', 'b5764b0d49664d4c8d946295a0515303',),
(1, 'fcrist3@uic.edu', 'b2db36767c9342e6a8a6654c6a50d086',),
(1, 'igupta5@uic.edu', '263b355e56494f73be99e5fe34fb01c1',),
(1, 'jmassi2@uic.edu', '5109a2de73884058b5e520d7e8b088f7',),
(1, 'jmassi2@uic.edu', 'd1109d3b3a3d44109ef8e88aecd5e5d0',),
(1, 'jyoon52@uic.edu', '2b7c0ea4a8014fa19a3136010a2f0dff',),
(1, 'jyoon52@uic.edu', 'd8ec0a3b9894435e8e4cddaf0efcc039',),
(1, 'lthomson@uic.edu', '327cd77f21cc472a8631f0e673e3070f',),
(1, 'lthomson@uic.edu', '5ff65c1da303448183f7cce22f5681fc',),
(1, 'mpope5@uic.edu', '511cbbd08bc04b1a9d5684db392417d5',),
(1, 'obhand2@uic.edu', '9f5c38a1ba8c477faab8294f97093986',),
(1, 'obhand2@uic.edu', 'cacc4a4fe91a4aa8bad335f63089ca8e',),
(1, 'pcabre4@uic.edu', '7f5e10dc08ca490683a5303564691c58',),
(1, 'pjha4@uic.edu', '248fab638e2a4b39b759ee40c8ba03a6',),
(1, 'pscisl2@uic.edu', 'e3f4b504ab3b4d8a9be385c0c4606730',),
(1, 'rholtz3@uic.edu', '132f559c8c804556a4acc8a3134ee367',),
(1, 'sfhassa2@uic.edu', '0d8e37a73d064176810cc7f78cc7378e',),
(1, 'snigam4@uic.edu', '35eb2c97eef84effa3fc93be6d4bbc4a',),
(1, 'snyderp@gmail.com', '6c3051a7379542c687253a6b3cddbd9a',),
(1, 'ssolan3@uic.edu', 'fd77441aa0574878bf522da7468c0360',),
(1, 'stanwa2@uic.edu', 'b224482feb594d4d8010d1380eb55684',),
(1, 'veenitgshah@gmail.com', '248fab638e2a4b39b759ee40c8ba03a6',),
(1, 'veenitgshah@gmail.com', 'b36ffc9637864478810f626fadf160fa',),
(1, 'vimalmish59@gmail.com', 'be0a9cc315f7413c9378814b5d978589',),
(1, 'vshah46@uic.edu', '6399426a1ded491383180d06e85598c6',),
(1, 'vshah46@uic.edu', 'b36ffc9637864478810f626fadf160fa',),
]

for _, email, install_id in data:
    for row in installs.find({'_id': install_id}, {"group": 1}):
        if not row:
            print email, install_id, "-"
            continue
        print email, row['_id'], row['group']
