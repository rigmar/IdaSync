from  difflib import *
from pprint import pprint

class MergedResult(object):

    def __init__(self):
        self.leftText = []
        self.rigthText = []
        self.diffs = {'-': {}, '+': {}}

    def parseDiff(self,diff):
        lineNumL = 0
        lineNumR = 0
        prevType = ""
        for l in diff:
            lineType = l[:1]
            line = l[2:]
            if lineType == " ":
                df = lineNumL - lineNumR
                if df < 0:
                    for s in range(0,abs(df)):
                        self.leftText.append((lineNumL, "\n", "!"))
                        lineNumL +=1
                elif df > 0:
                    for s in range(0,df):
                        self.rigthText.append((lineNumR, "\n", "!"))
                        lineNumR +=1

                self.leftText.append((lineNumL, line, lineType))
                self.rigthText.append((lineNumR, line, lineType))
                lineNumL += 1
                lineNumR += 1
            if lineType == "-":
                self.leftText.append((lineNumL, line, lineType))
                prevType = lineType
                lineNumL += 1
            if lineType == "+":
                self.rigthText.append((lineNumR, line, lineType))
                prevType = lineType
                lineNumR += 1
            if lineType == "?":
                # self.diffs.append((lineNumL if prevType == "-" else lineNumR,prevType) + (self.parseDiffLine(line),))
                self.diffs[prevType][lineNumL if prevType == "-" else lineNumR] = self.parseDiffLine(line)
                prevType = ""


    def parseDiffLine(self,line):
        raw = []
        i = 0
        line = line.strip("\n")
        for i, ch in enumerate(line):
            if ch != " ":
                raw.append((i,ch))
        ret = []
        i = 0
        if len(raw) > 1:
            startPos = raw[i][0]
            prevPos = startPos
            prevCH = raw[i][1]
            i += 1
            while i < len(raw):

                if prevPos + 1 == raw[i][0] and prevCH == raw[i][1]:
                    prevPos += 1
                else:
                    ret.append((startPos,prevPos,prevCH))
                    startPos = raw[i][0]
                    prevPos = startPos
                    prevCH = raw[i][1]
                i += 1
            ret.append((startPos, prevPos, prevCH))
        else:
            ret.append((raw[i][0], raw[i][0], raw[i][1]))

        return ret





s1 ='''struct test2
{
  int a1;
  __int16 a2;
  __unaligned __declspec(align(1)) int field_6;
  __int16 field_A;
  __int16 field_C;
};
'''.splitlines(True)

s2 = '''struct test2
{
  int a1;
  __int16 b2;
  __unaligned __declspec(align(1)) int field_6;
  unsigned __int16 field_A;
  __int16 Port;
  int a2;
  int a3;
};
'''.splitlines(True)


d = Differ()

result = list(d.compare(s1, s2))
#print result

#pprint(result)

MR = MergedResult()
MR.parseDiff(result)
print MR.leftText
print MR.diffs


for l in result:
    print l.strip("\n\r")
result = list(d.compare("  __int16 field_C;", "  _WORD Port;"))
for l in result:
    print l.strip("\n\r")
d = HtmlDiff()
#print d.make_table(s1, s2)