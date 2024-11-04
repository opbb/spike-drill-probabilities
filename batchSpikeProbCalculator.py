import math
from typing import Dict, List
import numpy as np
from numpy._typing import NDArray
import datetime
from math import comb, pow
import json
import tracemalloc
import os

# == BATCH SETTINGS ==
minTotalSystems: int = 1
maxTotalSystems: int = 130
minMinSuccessfulRoll = 3
maxMinSuccessfulRoll = 13
totalRunsCounter: int = 0


# == SETUP VARS ==
# The limit to the number of rolls this will brute force calculate.
# (Needed to stop infinite recursion from the "Off course caught early" mishap you get on a roll of 13-15,
# which could go on forever even while taking life support reserves into account)
maxRolls: int = 100

# The total number of "systems" which the ship has, including the spike drive.
# This affects success prob cause more systems means less chance that the
# spike drive is disabled by a power spike on a mishap roll of 6-8.
# What exactly a "system" is is never defined, so its kinda up to the GM.
totalSystems: int

# Indices of arrays in probs list
outcomeProbsListIndex = 0
spikeDurationProbsListIndex = 1
systemsDisabledProbsListIndex = 2

# Indices of outcome types in arrays
successIndex = 0
recoverableFailIndex = 1
catastrophicFailIndex = 2
maxRollsIndex = 3

# Dice Probabilities
twoDSixOrGreaterProbs = [
    1,
    1,
    36 / 36,
    35 / 36,
    33 / 36,
    30 / 36,
    26 / 36,
    21 / 36,
    15 / 36,
    10 / 36,
    6 / 36,
    3 / 36,
    1 / 36,
    0,
    0,
    0,
]


threeDSixProbs = [
    0,
    0,
    0,
    1 / 216,
    3 / 216,
    6 / 216,
    10 / 216,
    15 / 216,
    21 / 216,
    25 / 216,
    27 / 216,
    27 / 216,
    25 / 216,
    21 / 216,
    15 / 216,
    10 / 216,
    6 / 216,
    3 / 216,
    1 / 216,
    0,
    0,
    0,
]

# Spike Check probs
spikeCheckSuccessProb: float
spikeCheckFailProb: float

## Mishap table probs
catastrophicDimensionalEnergyIncursion: float
shearSurge: float
powerSpike: float
offCourse: float
offCourseCaughtEarly: float
slowSuccess: float
dumbLuckSuccess: float

### Normal mishap probs
catastrophicDimensionalEnergyIncursionDefault: float = threeDSixProbs[3]
shearSurgeDefault: float = threeDSixProbs[4] + threeDSixProbs[5]
powerSpikeDefault: float = threeDSixProbs[6] + threeDSixProbs[7] + threeDSixProbs[8]
offCourseDefault: float = threeDSixProbs[9] + threeDSixProbs[10] + threeDSixProbs[11] + threeDSixProbs[12]
offCourseCaughtEarlyDefault: float =  threeDSixProbs[13] + threeDSixProbs[14] + threeDSixProbs[15]
slowSuccessDefault: float =  threeDSixProbs[16] + threeDSixProbs[17]
dumbLuckSuccessDefault: float = threeDSixProbs[18]

### Mishap probs with precog nav chamber
catastrophicDimensionalEnergyIncursionPrecog = 0
shearSurgePrecog = threeDSixProbs[3]
powerSpikePrecog = threeDSixProbs[4] + threeDSixProbs[5] + threeDSixProbs[6]
offCoursePrecog = threeDSixProbs[7] + threeDSixProbs[8] + threeDSixProbs[9] + threeDSixProbs[10]
offCourseCaughtEarlyPrecog =  threeDSixProbs[11] + threeDSixProbs[12] + threeDSixProbs[13]
slowSuccessPrecog =  threeDSixProbs[14] + threeDSixProbs[15]
dumbLuckSuccessPrecog = threeDSixProbs[16] + threeDSixProbs[17] + threeDSixProbs[18]

# Dynamic programming so this isn't O(N^3)
memoizationTable: Dict[str, List[NDArray]] = {}

# List of 3 arrays.
# One for the overall probability of each outcome (success, recoverable failure, catastrophic failure, and max rolls)
# One for the probability of each number of spike durations passing for each outcomes. (ie whats the probability of a recoverable failure after 15 spike durations?)
# One for the probability of each number of systems being disabled for each outcome. (ie whats the probability of a successful outcome with 6 systems disabled?)
probs: List[NDArray] = []

outcomesTemplateList: List[float] = [0.0,0.0,0.0,0.0]

# Generate a list with maxRolls + 2 items in it, to represent the possibility of a number of spikeDurations passing equal to 0 through maxRolls + 1.
# Max spike durations passed is maxRolls + 1 because they could be off course until the last roll, then get a slow, dumb-luck success
spikeDurationsPassedTemplateList: List[float] = [0.0]
for i in range(maxRolls + 1):
    spikeDurationsPassedTemplateList.append(0.0)

# This will be generated for every run, as it changes.
systemsDisabledTemplateList: List[float]
systemsDisabledTemplateArray: NDArray
recoverableFailSystemsDisabledMemoizationDict: Dict[int, NDArray]

outcomesTemplateArray:NDArray = np.array(outcomesTemplateList)
spikeDurationsPassedTemplateArray: NDArray = np.array([spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList])


# Creates a new list by multiplying all values in probs by a probability
def applyProb(probs: List[NDArray], prob: float) -> List[NDArray]:
    retProbs: List[NDArray] = [np.array([]), np.array([]), np.array([])]

    retProbs[outcomeProbsListIndex] = probs[outcomeProbsListIndex] * prob
    retProbs[spikeDurationProbsListIndex] = probs[spikeDurationProbsListIndex] * prob
    retProbs[systemsDisabledProbsListIndex] = probs[systemsDisabledProbsListIndex] * prob

    return retProbs

# Creates a new list by adding the values in two probs lists together.
def addProbs(probs1: List[NDArray], probs2: List[NDArray]) -> List[NDArray]:
    retProbs: List[NDArray] = [np.array([]), np.array([]), np.array([])]

    retProbs[outcomeProbsListIndex] = np.add(probs1[outcomeProbsListIndex], probs2[outcomeProbsListIndex])
    retProbs[spikeDurationProbsListIndex] = np.add(probs1[spikeDurationProbsListIndex], probs2[spikeDurationProbsListIndex])
    retProbs[systemsDisabledProbsListIndex] = np.add(probs1[systemsDisabledProbsListIndex], probs2[systemsDisabledProbsListIndex])

    return retProbs

# Calculates the probability that X systems out of Y will be disabled when each has a 50% chance to be disabled.
probOfXSysDisabledMemoizationDict = {}
counter = 0
def calculateProbOfXSystemsDisabledOnRecoverableFail(nonSpikeSystemsFunctional: int, numToDisable: int) -> float:
    global probOfXSysDisabledMemoizationDict
    caseKey = str(nonSpikeSystemsFunctional) + ',' + str(numToDisable)
    if caseKey in probOfXSysDisabledMemoizationDict:
        return probOfXSysDisabledMemoizationDict[caseKey]

    # Using coin flip formula from here https://www.omnicalculator.com/statistics/coin-flip-probability
    caseValue = comb(nonSpikeSystemsFunctional, numToDisable) / pow(2, nonSpikeSystemsFunctional)
    probOfXSysDisabledMemoizationDict[caseKey] = caseValue

    return caseValue

# Creates a string with all args of calculateProbsRecursion, used as the key in the memoization table.
def argsToString(systemsDisabled: int, rollNumber: int, spikeDurationsPassed: int) -> str:
    return str(systemsDisabled) + "," + str(rollNumber) + "," + str(spikeDurationsPassed)

# Calculates probs given the current setup vars, and returns the results
def calculateProbs(totalSys: int, minSuccessfulRoll: int, isUsingPrecogNavChamber: bool) -> List[NDArray]:
    global memoizationTable
    memoizationTable = {}

    global totalSystems, systemsDisabledTemplateArray, systemsDisabledTemplateList
    totalSystems = totalSys
    # Generate a list with totalSystems + 1 items in it, to represent the possibility of a number of systems equal to 0 through totalSystems being disabled.
    systemsDisabledTemplateList = [0.0]
    for i in range(totalSystems):
        systemsDisabledTemplateList.append(0.0)
    systemsDisabledTemplateArray = np.array([systemsDisabledTemplateList,systemsDisabledTemplateList,systemsDisabledTemplateList,systemsDisabledTemplateList])

    global spikeCheckSuccessProb, spikeCheckFailProb
    spikeCheckSuccessProb = twoDSixOrGreaterProbs[minSuccessfulRoll]
    spikeCheckFailProb = 1 - spikeCheckSuccessProb

    global dumbLuckSuccess, slowSuccess, offCourseCaughtEarly, offCourse, powerSpike, shearSurge, catastrophicDimensionalEnergyIncursion
    if isUsingPrecogNavChamber:
        dumbLuckSuccess = dumbLuckSuccessPrecog
        slowSuccess = slowSuccessPrecog
        offCourseCaughtEarly = offCourseCaughtEarlyPrecog
        offCourse = offCoursePrecog
        powerSpike = powerSpikePrecog
        shearSurge = shearSurgePrecog
        catastrophicDimensionalEnergyIncursion = catastrophicDimensionalEnergyIncursionPrecog
    else:
        dumbLuckSuccess = dumbLuckSuccessDefault
        slowSuccess = slowSuccessDefault
        offCourseCaughtEarly = offCourseCaughtEarlyDefault
        offCourse = offCourseDefault
        powerSpike = powerSpikeDefault
        shearSurge = shearSurgeDefault
        catastrophicDimensionalEnergyIncursion = catastrophicDimensionalEnergyIncursionDefault

    probs = calculateProbsRecursion(0,0,0)

    del memoizationTable

    return probs

# Calculates the probability of each possible outcome given the current number of systems disable, what roll it is, and how much time has passed.
# Uses memoization to not be O(3^n)
def calculateProbsRecursion(systemsDisabled: int, rollNumber: int, spikeDurationsPassed: int) -> List[NDArray]:
    rollNumber += 1
    argsString = argsToString(systemsDisabled, rollNumber, spikeDurationsPassed)

    # Check if we've calculated this previously'
    if argsString in memoizationTable:
        return memoizationTable[argsString].copy()

    global totalRunsCounter
    totalRunsCounter += 1

    probs = [
        outcomesTemplateArray.copy(),
        spikeDurationsPassedTemplateArray.copy(),
        systemsDisabledTemplateArray.copy(),
    ]

    if rollNumber > maxRolls:
        probs[outcomeProbsListIndex][maxRollsIndex] += 1.0
        probs[spikeDurationProbsListIndex][maxRollsIndex, spikeDurationsPassed] += 1.0
        probs[systemsDisabledProbsListIndex][maxRollsIndex, systemsDisabled] += 1.0
        return probs

    # Successful Check
    caseProb = spikeCheckSuccessProb
    probs[outcomeProbsListIndex][successIndex] += caseProb
    probs[spikeDurationProbsListIndex][successIndex, spikeDurationsPassed + 1] += caseProb
    probs[systemsDisabledProbsListIndex][successIndex, systemsDisabled] += caseProb

    # Failed Checks / Mishap Rolls

    ## Dumb luck success, 18
    caseProb = spikeCheckFailProb * dumbLuckSuccess
    probs[outcomeProbsListIndex][successIndex] += caseProb
    probs[spikeDurationProbsListIndex][successIndex, spikeDurationsPassed + 1] += caseProb
    probs[systemsDisabledProbsListIndex][successIndex, systemsDisabled] += caseProb

    ## Dumb luck slow success, 16-17
    caseProb = spikeCheckFailProb * slowSuccess
    probs[outcomeProbsListIndex][successIndex] += caseProb
    probs[spikeDurationProbsListIndex][successIndex, spikeDurationsPassed + 2] += caseProb
    probs[systemsDisabledProbsListIndex][successIndex, systemsDisabled] += caseProb

    ## Off course caught early, 13-15
    caseProb = spikeCheckFailProb * offCourseCaughtEarly
    if caseProb > 0:
        probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled, rollNumber, spikeDurationsPassed), caseProb))

    ## Off course, 9-12
    caseProb = spikeCheckFailProb * offCourse
    if caseProb > 0:
        probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled, rollNumber, spikeDurationsPassed + 1), caseProb))

    ## Off course, power spike, 6-8
    ### Non-spike system is disabled
    # if case avoids unnecessary work and divide by zero errors
    if totalSystems > systemsDisabled + 1:
        caseProb = spikeCheckFailProb * powerSpike * ((totalSystems - systemsDisabled - 1) / (totalSystems - systemsDisabled))
        if caseProb > 0:
            probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled + 1, rollNumber, spikeDurationsPassed + 1), caseProb))

    ### Spike system is disabled
    caseProb = spikeCheckFailProb * powerSpike * (1 / (totalSystems - systemsDisabled))
    probs[outcomeProbsListIndex][catastrophicFailIndex] += caseProb
    probs[systemsDisabledProbsListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[spikeDurationProbsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    ## Maybe recoverable failure, 4-5
    ### Spike system not disabled
    caseProb = spikeCheckFailProb * shearSurge * 0.5
    probs[outcomeProbsListIndex][recoverableFailIndex] += caseProb
    probs[spikeDurationProbsListIndex][recoverableFailIndex, spikeDurationsPassed + 1] += caseProb

    nonSpikeSystemsFunctional = totalSystems - systemsDisabled - 1
    if nonSpikeSystemsFunctional not in recoverableFailSystemsDisabledMemoizationDict:
        caseValues = np.array(systemsDisabledTemplateList)
        for numToDisable in range(0, totalSystems - systemsDisabled, 1):
            caseValues[systemsDisabled + numToDisable] += calculateProbOfXSystemsDisabledOnRecoverableFail(nonSpikeSystemsFunctional, numToDisable)
        recoverableFailSystemsDisabledMemoizationDict[nonSpikeSystemsFunctional] = caseValues
    probs[systemsDisabledProbsListIndex][recoverableFailIndex] = np.add(probs[systemsDisabledProbsListIndex][recoverableFailIndex], caseProb * recoverableFailSystemsDisabledMemoizationDict[nonSpikeSystemsFunctional])

    ### Spike system disabled
    caseProb = spikeCheckFailProb * shearSurge * 0.5
    probs[outcomeProbsListIndex][catastrophicFailIndex] += caseProb
    probs[systemsDisabledProbsListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[spikeDurationProbsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    ## Catastrophic failure, 3
    caseProb = spikeCheckFailProb * catastrophicDimensionalEnergyIncursion
    probs[outcomeProbsListIndex][catastrophicFailIndex] += caseProb
    probs[systemsDisabledProbsListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[spikeDurationProbsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    # Memoize this branch
    memoizationTable[argsString] = probs.copy()

    return probs


def formatProbsObjKey(totalSys: int, minSuccessfulRoll: int, isUsingPrecogNavChamber: bool) -> str:
    return str(totalSys) + ',' + str(minSuccessfulRoll) + ',' + ('1' if isUsingPrecogNavChamber else '0')

def formatProbsObj(probs: List[NDArray]):
    return {
        'success': {
            'totalProb': probs[outcomeProbsListIndex][successIndex],
            'spikeDurationProbs': probs[spikeDurationProbsListIndex][successIndex].tolist(),
            'numSystemsDisabledProbs': probs[systemsDisabledProbsListIndex][successIndex].tolist()
        },
        'recoverableFailure': {
            'totalProb': probs[outcomeProbsListIndex][recoverableFailIndex],
            'spikeDurationProbs': probs[spikeDurationProbsListIndex][recoverableFailIndex].tolist(),
            'numSystemsDisabledProbs': probs[systemsDisabledProbsListIndex][recoverableFailIndex].tolist()
        },
        'catastrophicFailure': {
            'totalProb': probs[outcomeProbsListIndex][catastrophicFailIndex],
            'spikeDurationProbs': probs[spikeDurationProbsListIndex][catastrophicFailIndex].tolist(),
            'numSystemsDisabledProbs': probs[systemsDisabledProbsListIndex][catastrophicFailIndex].tolist()
        }
    }

startTime = datetime.datetime.now()

probsData = {}
totalCases = (maxTotalSystems - minTotalSystems + 1) * (maxMinSuccessfulRoll - minMinSuccessfulRoll + 1) * 2
currentCase = 0

probsDirName = "spikeProbs"
os.makedirs(os.getcwd() + '/' + probsDirName, exist_ok=True)

for totalSys in range(minTotalSystems, maxTotalSystems + 1, 1):
    recoverableFailSystemsDisabledMemoizationDict = {}
    for minSuccessfulRoll in range(minMinSuccessfulRoll, maxMinSuccessfulRoll + 1, 1):
        for isUsingPrecogNavChamber in [False, True]:
            caseStartTime = datetime.datetime.now()
            currentCase += 1

            probs = calculateProbs(totalSys=totalSys, minSuccessfulRoll=minSuccessfulRoll, isUsingPrecogNavChamber=isUsingPrecogNavChamber)

            # Make spike duration and system disabled probabilities based on the assumption that their outcome was selected.
            probs[spikeDurationProbsListIndex] = probs[spikeDurationProbsListIndex] / probs[outcomeProbsListIndex][:, np.newaxis]
            probs[systemsDisabledProbsListIndex] = probs[systemsDisabledProbsListIndex] / probs[outcomeProbsListIndex][:, np.newaxis]

            probsKey = formatProbsObjKey(totalSys=totalSys, minSuccessfulRoll=minSuccessfulRoll, isUsingPrecogNavChamber=isUsingPrecogNavChamber)
            probsObj = formatProbsObj(probs)

            # Clear previous line
            print("                                                                                                                 ", end='\r')

            totalProbsSum = np.sum(probs[outcomeProbsListIndex])
            if round(totalProbsSum, 5) != 1.0:
                print("Case ", probsKey," total probs sum to ", totalProbsSum, " instead of 1.0!")

            currentTime = datetime.datetime.now()
            caseTime = currentTime - caseStartTime
            totalTime = currentTime - startTime
            print("case ", currentCase, "/", totalCases, "\ttotal time (s): ", "{:.3f}".format(round(totalTime.total_seconds(), 3)), "\tcase time (s): ", "{:.3f}".format(round(caseTime.total_seconds(), 3)), "\tcase key: ", probsKey, sep='', end='\r')

            probsData[probsKey] = probsObj

    # Store probs data in file once for every number of total systems
    # This minimizes slowdown due to excess memory use
    #with open(probsDirName + '/' + str(totalSys) + 'TotalSystemsSpikeProbs.json', 'w') as f:
    #    # dump data as json
    #    json.dump(probsData, f, ensure_ascii=False, indent=4)
    with open(probsDirName + '/' + str(totalSys) + 'TotalSystemsSpikeProbs.json', 'r') as f:
        fileData = json.load(f)

    fileData.update(probsData)

    with open(probsDirName + '/' + str(totalSys) + 'TotalSystemsSpikeProbs.json', 'w') as f:
        json.dump(fileData, f, ensure_ascii=False, indent=4)
    del probsData
    probsData = {}

endTime = datetime.datetime.now()
timeDiff = endTime - startTime

print("== PROGRAM STATS ==")
print("Total Runs Counter: ", totalRunsCounter)
print("Total time (s): ", timeDiff.total_seconds())
