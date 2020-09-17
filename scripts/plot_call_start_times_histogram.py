import matplotlib.pyplot as plt
import numpy as np


start_time_counts = '''
28,1
30,1
35,1
38,2
42,1
46,1
48,1
51,1
52,1
55,1
57,1
61,3
62,2
66,1
68,2
71,3
72,6
73,3
74,4
75,2
76,5
78,5
79,1
80,14
81,1
82,10
83,4
84,13
85,4
86,15
87,3
88,23
89,10
90,13
91,2
92,37
93,6
94,49
95,8
96,72
97,12
98,94
99,18
100,124
101,22
102,145
103,45
104,206
105,42
106,324
107,49
108,386
109,126
110,402
111,151
112,669
113,69
114,888
115,101
116,1083
117,95
118,1106
119,88
120,1253
121,82
122,1283
123,75
124,1391
125,57
126,1286
127,47
128,1071
129,93
130,559
131,51
132,118
134,1
144,1
145,1
148,2
160,1
162,2
166,1
167,1
169,1
170,1
172,3
174,1
186,4
191,1
194,1
196,1
201,2
202,3
204,1
208,1
209,1
212,1
226,1
238,1
258,1
276,1
282,1
284,1
292,1
295,1
299,1
316,1
324,1
336,1
338,2
350,1
352,1
361,1
572,1
584,1
761,1
795,1
849,1
'''


def main():
    counts = get_counts()
    plot_counts(counts)
    
    
def get_counts():
    
    lines = start_time_counts.strip().split('\n')
    pairs = [parse_line(line) for line in lines]
    counts_dict = dict(pairs)
    
    max_start_time = pairs[-1][0]
    if max_start_time % 2 == 0:
        max_start_time += 1
    counts = np.zeros(max_start_time + 1, dtype='int')
    
    for start_time, count in counts_dict.items():
        counts[start_time] = count
        
    counts = counts[0::2] + counts[1::2]
        
    for i, count in enumerate(counts):
        print(2 * i, count)
        
    return counts
    
    
def parse_line(line):
    start_time, count = line.split(',')
    return int(start_time), int(count)


def plot_counts(counts):
    start_times = 2 * np.arange(len(counts))
    plt.plot(start_times, counts, '*')
    plt.xlim(60, 160)
    plt.show()


if __name__ == '__main__':
    main()
