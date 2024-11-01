import math
from typing import Dict, List
import numpy as np
from numpy._typing import NDArray
import datetime
from math import comb, pow

# == SETUP VARS ==
# The limit to the number of rolls this will brute force calculate.
# (Needed to stop infinite recursion from the "Off course caught early" mishap you get on a roll of 13-15,
# which could go on forever even while taking life support reserves into account)
maxRolls: int = 100

# The total number of "systems" which the ship has, including the spike drive.
# This affects success prob cause more systems means less chance that the
# spike drive is disabled by a power spike on a mishap roll of 6-8.
# What exactly a "system" is is never defined, so its kinda up to the GM.
totalSystems: int = 200

# The drill distance in hexes. Affects DC and spikeDuration.
drillDistance: int = 3

# The drive rating of the ships drive BEFORE any modifiers are applied.
baseDriveRating: int = 2

# The pilot's level in the Pilot skill. Use -1 for no levels
pilotSkillLevel = 0

# The pilot's int modifier
pilotIntMod = 0

# Any random modifiers to the DC of the spike check that are not already accounted for.
# It is important to distinguish between mods to the check and mods to the DC, because if the DC is
# lower than 6 then the check automatically succeeds.
miscSpikeDCMods = 0

# The age of the rutter in Estude days. Is the primary determiner of spike difficulty.
# A value of None represents no rutter, ie. a blind punch.
rutterAge: None | float = 100

# Whether or not the pilot is trimming the course.
# Trimming the course decreases spike duration, but increases the DC.
isTrimmingCourse: bool = False

# Whether or not the activation of the drill was rushed.
# Making a spike drill usually takes 30 mins, but can be done in 1 round of space combat if rushed.
# Rushing the activation increases DC.
wasDrillActivationRushed: bool = False

# Whether or not the ship is equipped with and using a precognitive nav chamber.
isUsingPrecogNavChamber: bool = False

# Whether or not the ship is equipped with and using an advanced nav computer.
isUsingAdvancedNavComputer: bool = False

# The pilot's level of the Starfarer focus. 0 for if they don't have it.
pilotStarfarerLevel: int = 0

# Whether or not the ship is equipped with and using a drill course regulator.
isUsingDrillCourseRegulator: bool = False

# Whether or not the ship's drive has the Drill Velocity Upgrade mod.
hasDrillVelocityUpgrade: bool = True

# The number of decimal places to round to in the output.
# Only affects printed numbers, not the underlying data.
roundTo = 3



# == CALCULATED VARS ==
# The conversion from one earth day to one Es day.
earthDaysToEsDays: float = 24.0 / 33.6

effectiveDriveRating: int = baseDriveRating + (1 if pilotStarfarerLevel == 2 else 0) + (1 if hasDrillVelocityUpgrade else 0) + (1 if isTrimmingCourse else 0)

# The amount of time that 1 spike check will take.
# With mishaps, the actual time taken will usually be a multiple of this.
spikeDuration = (6.0 * drillDistance * earthDaysToEsDays) / (effectiveDriveRating + (1 if isTrimmingCourse else 0))

intPilotMod: int = (pilotSkillLevel * (2 if pilotStarfarerLevel == 2 else 1)) + pilotIntMod

# The spike check DC at which you cannot fail
autoSuccessDC: int = 6
if isUsingPrecogNavChamber:
    autoSuccessDC = 9
if pilotStarfarerLevel == 1 or pilotStarfarerLevel == 2:
    autoSuccessDC = 10

# Determine spike DC
drillDC: int = 7
if rutterAge == None:
    # Completely uncharted, blind punch
    drillDC += 6
elif rutterAge > (365 * 5) * earthDaysToEsDays:
    # Rutter is more that 5 earth years old
    drillDC += 2
elif rutterAge > 365 * earthDaysToEsDays:
    # Rutter is 1-5 earth years old
    drillDC += 1
elif rutterAge > 30 * earthDaysToEsDays:
    # Rutter is 1-12 earth months old
    drillDC += 0
elif rutterAge > 0:
    # Rutter is less than 1 earth month old
    drillDC += -2
else:
    print("Rutter age shouldn't be negative")
    exit()

drillDC += math.floor(drillDistance / 2.0)
drillDC += 2 if isTrimmingCourse else 0
drillDC += 2 if wasDrillActivationRushed else 0
drillDC += -2 if isUsingAdvancedNavComputer and rutterAge != None and rutterAge <= 365.25 * earthDaysToEsDays else 0
drillDC += miscSpikeDCMods

# Indices of arrays in probs list
outcomesListIndex = 0
avgSpikeDurationsListIndex = 1
avgSystemsDisabledListIndex = 2

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
spikeCheckSuccessProb = twoDSixOrGreaterProbs[drillDC - intPilotMod]
if drillDC <= autoSuccessDC:
    # Drills of DC 6 or lower auto-succeed. This number can be changed by foci or fittings.
    spikeCheckSuccessProb = 1.0
if isUsingDrillCourseRegulator and rutterAge != None and not isTrimmingCourse and drillDistance <= pilotSkillLevel * 2:
    # Routine drills with the drill course regulator fitting auto-succeed
    spikeCheckSuccessProb = 1.0
spikeCheckFailProb = 1 - spikeCheckSuccessProb

## Mishap table probs
catastrophicDimensionalEnergyIncursion: float = threeDSixProbs[3]
shearSurge: float = threeDSixProbs[4] + threeDSixProbs[5]
powerSpike: float = threeDSixProbs[6] + threeDSixProbs[7] + threeDSixProbs[8]
offCourse: float = threeDSixProbs[9] + threeDSixProbs[10] + threeDSixProbs[11] + threeDSixProbs[12]
offCourseCaughtEarly: float =  threeDSixProbs[13] + threeDSixProbs[14] + threeDSixProbs[15]
slowSuccess: float =  threeDSixProbs[16] + threeDSixProbs[17]
dumbLuckSuccess: float = threeDSixProbs[18]

if isUsingPrecogNavChamber:
    catastrophicDimensionalEnergyIncursion = 0
    shearSurge = threeDSixProbs[3]
    powerSpike = threeDSixProbs[4] + threeDSixProbs[5] + threeDSixProbs[6]
    offCourse = threeDSixProbs[7] + threeDSixProbs[8] + threeDSixProbs[9] + threeDSixProbs[10]
    offCourseCaughtEarly =  threeDSixProbs[11] + threeDSixProbs[12] + threeDSixProbs[13]
    slowSuccess =  threeDSixProbs[14] + threeDSixProbs[15]
    dumbLuckSuccess = threeDSixProbs[16] + threeDSixProbs[17] + threeDSixProbs[18]

# Dynamic programming so this isn't O(N^3)
memoizationTable: Dict = {}

# List of 3 arrays.
# One for the overall probability of each outcome (success, recoverable failure, catastrophic failure, and max rolls)
# One for the probability of each number of spike durations passing for each outcomes. (ie whats the probability of a recoverable failure after 15 spike durations?)
# One for the probability of each number of systems being disabled for each outcome. (ie whats the probability of a successful outcome with 6 systems disabled?)
probs: List[NDArray] = []

outcomesTemplateList: List[float] = [0.0,0.0,0.0,0.0]

# Generate a list with totalSystems + 1 items in it, to represent the possibility of a number of systems equal to 0 through totalSystems being disabled.
systemsDisabledTemplateList: List[float] = [0.0]
for i in range(totalSystems):
    systemsDisabledTemplateList.append(0.0)

# Generate a list with maxRolls + 2 items in it, to represent the possibility of a number of spikeDurations passing equal to 0 through maxRolls + 1.
# Max spike durations passed is maxRolls + 1 because they could be off course until the last roll, then get a slow, dumb-luck success
spikeDurationsPassedTemplateList: List[float] = [0.0]
for i in range(maxRolls + 1):
    spikeDurationsPassedTemplateList.append(0.0)

outcomesTemplateArray = np.array(outcomesTemplateList)
spikeDurationsPassedTemplateArray = np.array([spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList,spikeDurationsPassedTemplateList])
systemsDisabledTemplateArray = np.array([systemsDisabledTemplateList,systemsDisabledTemplateList,systemsDisabledTemplateList,systemsDisabledTemplateList])

# Creates a new list by multiplying all values in probs by a probability
def applyProb(probs: List[NDArray], prob: float) -> List[NDArray]:
    retProbs: List[NDArray] = [np.array([]), np.array([]), np.array([])]

    retProbs[outcomesListIndex] = probs[outcomesListIndex] * prob
    retProbs[avgSpikeDurationsListIndex] = probs[avgSpikeDurationsListIndex] * prob
    retProbs[avgSystemsDisabledListIndex] = probs[avgSystemsDisabledListIndex] * prob

    return retProbs

# Creates a new list by adding the values in two probs lists together.
def addProbs(probs1: List[NDArray], probs2: List[NDArray]) -> List[NDArray]:
    retProbs: List[NDArray] = [np.array([]), np.array([]), np.array([])]

    retProbs[outcomesListIndex] = np.add(probs1[outcomesListIndex], probs2[outcomesListIndex])
    retProbs[avgSpikeDurationsListIndex] = np.add(probs1[avgSpikeDurationsListIndex], probs2[avgSpikeDurationsListIndex])
    retProbs[avgSystemsDisabledListIndex] = np.add(probs1[avgSystemsDisabledListIndex], probs2[avgSystemsDisabledListIndex])

    return retProbs

# Calculates the probability that X systems out of Y will be disabled when each has a 50% chance to be disabled.
def calculateProbOfXSystemsDisabledOnRecoverableFail(nonSpikeSystemsFunctional: int, numToDisable: int) -> float:
    # Using coin flip formula from here https://www.omnicalculator.com/statistics/coin-flip-probability
    return comb(nonSpikeSystemsFunctional, numToDisable) / pow(2, nonSpikeSystemsFunctional)

# Creates a string with all args of calculateProbsRecursion, used as the key in the memoization table.
def argsToString(systemsDisabled: int, rollNumber: int, spikeDurationsPassed: int) -> str:
    return str(systemsDisabled) + "," + str(rollNumber) + "," + str(spikeDurationsPassed)

def formatProbAsPercent(prob: float) -> str:
    return str(round(prob * 100.0, roundTo)) + "%"

# Calculates probs given the current setup vars, and returns the results
def calculateProbs() -> List[NDArray]:
    memoizationTable = {}
    probs = calculateProbsRecursion(0,0,0)
    return probs

# Calculates the probability of each possible outcome given the current number of systems disable, what roll it is, and how much time has passed.
# Uses memoization to not be O(n^3)
def calculateProbsRecursion(systemsDisabled: int, rollNumber: int, spikeDurationsPassed: int) -> List[NDArray]:
    rollNumber += 1
    argsString = argsToString(systemsDisabled, rollNumber, spikeDurationsPassed)

    # Check if we've calculated this previously'
    if argsString in memoizationTable:
        return memoizationTable[argsString].copy()

    probs = [
        outcomesTemplateArray.copy(),
        spikeDurationsPassedTemplateArray.copy(),
        systemsDisabledTemplateArray.copy(),
    ]

    if rollNumber > maxRolls:
        probs[outcomesListIndex][maxRollsIndex] += 1.0
        probs[avgSpikeDurationsListIndex][maxRollsIndex, spikeDurationsPassed] += 1.0
        probs[avgSystemsDisabledListIndex][maxRollsIndex, systemsDisabled] += 1.0
        return probs

    # Successful Check
    caseProb = spikeCheckSuccessProb
    probs[outcomesListIndex][successIndex] += caseProb
    probs[avgSpikeDurationsListIndex][successIndex, spikeDurationsPassed + 1] += caseProb
    probs[avgSystemsDisabledListIndex][successIndex, systemsDisabled] += caseProb

    # Failed Checks / Mishap Rolls

    ## Dumb luck success, 18
    caseProb = spikeCheckFailProb * dumbLuckSuccess
    probs[outcomesListIndex][successIndex] += caseProb
    probs[avgSpikeDurationsListIndex][successIndex, spikeDurationsPassed + 1] += caseProb
    probs[avgSystemsDisabledListIndex][successIndex, systemsDisabled] += caseProb

    ## Dumb luck slow success, 16-17
    caseProb = spikeCheckFailProb * slowSuccess
    probs[outcomesListIndex][successIndex] += caseProb
    probs[avgSpikeDurationsListIndex][successIndex, spikeDurationsPassed + 2] += caseProb
    probs[avgSystemsDisabledListIndex][successIndex, systemsDisabled] += caseProb

    ## Off course caught early, 13-15
    caseProb = spikeCheckFailProb * offCourseCaughtEarly
    probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled, rollNumber, spikeDurationsPassed), caseProb))

    ## Off course, 9-12
    caseProb = spikeCheckFailProb * offCourse
    probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled, rollNumber, spikeDurationsPassed + 1), caseProb))

    ## Off course, power spike, 6-8
    ### Non-spike system is disabled
    # if case avoids unnecessary work and divide by zero errors
    if totalSystems > systemsDisabled + 1:
        caseProb = spikeCheckFailProb * powerSpike * ((totalSystems - systemsDisabled - 1) / (totalSystems - systemsDisabled))
        probs = addProbs(probs, applyProb(calculateProbsRecursion(systemsDisabled + 1, rollNumber, spikeDurationsPassed + 1), caseProb))

    ### Spike system is disabled
    caseProb = spikeCheckFailProb * powerSpike * (1 / (totalSystems - systemsDisabled))
    probs[outcomesListIndex][catastrophicFailIndex] += caseProb
    probs[avgSystemsDisabledListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[avgSpikeDurationsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    ## Maybe recoverable failure, 4-5
    ### Spike system not disabled
    caseProb = spikeCheckFailProb * shearSurge * 0.5
    probs[outcomesListIndex][recoverableFailIndex] += caseProb
    probs[avgSpikeDurationsListIndex][recoverableFailIndex, spikeDurationsPassed + 1] += caseProb

    nonSpikeSystemsFunctional = totalSystems - systemsDisabled - 1
    for numToDisable in range(0, totalSystems - systemsDisabled, 1):
        probs[avgSystemsDisabledListIndex][recoverableFailIndex, numToDisable] += caseProb * calculateProbOfXSystemsDisabledOnRecoverableFail(nonSpikeSystemsFunctional, numToDisable)

    ### Spike system disabled
    caseProb = spikeCheckFailProb * shearSurge * 0.5
    probs[outcomesListIndex][catastrophicFailIndex] += caseProb
    probs[avgSystemsDisabledListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[avgSpikeDurationsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    ## Catastrophic failure, 3
    caseProb = spikeCheckFailProb * catastrophicDimensionalEnergyIncursion
    probs[outcomesListIndex][catastrophicFailIndex] += caseProb
    probs[avgSystemsDisabledListIndex][catastrophicFailIndex, totalSystems] += caseProb
    probs[avgSpikeDurationsListIndex][catastrophicFailIndex, spikeDurationsPassed + 1] += caseProb

    # Memoize this branch
    memoizationTable[argsString] = probs.copy()

    return probs

startTime = datetime.datetime.now()

probs = calculateProbs()

endTime = datetime.datetime.now()
timeDiff = endTime - startTime

# Make spike duration and system disabled probabilities based on the assumption that their outcome was selected.
normalizedSpikeDurations = probs[1] / probs[0][:, np.newaxis]
normalizedSystemsDisabled = probs[2] / probs[0][:, np.newaxis]

# Create stat strings
spikeDurationStatStrings = ["","","",""]
systemsDisabledStatStrings = ["","","",""]
avgSpikeDurations = [0.0,0.0,0.0,0.0]
avgSystemsDisabled = [0.0,0.0,0.0,0.0]
for i in range(maxRolls + 2):
    label = str(round(i * spikeDuration, 1)) + ": "
    separator = "" if i >= maxRolls + 1 else ", "
    spikeDurationStatStrings[successIndex] += label + formatProbAsPercent(normalizedSpikeDurations[successIndex, i]) + separator
    avgSpikeDurations[successIndex] += normalizedSpikeDurations[successIndex, i] * i
    spikeDurationStatStrings[recoverableFailIndex] += label + formatProbAsPercent(normalizedSpikeDurations[recoverableFailIndex, i]) + separator
    avgSpikeDurations[recoverableFailIndex] += normalizedSpikeDurations[recoverableFailIndex, i] * i
    spikeDurationStatStrings[catastrophicFailIndex] += label + formatProbAsPercent(normalizedSpikeDurations[catastrophicFailIndex, i]) + separator
    avgSpikeDurations[catastrophicFailIndex] += normalizedSpikeDurations[catastrophicFailIndex, i] * i
    spikeDurationStatStrings[maxRollsIndex] += label + formatProbAsPercent(normalizedSpikeDurations[maxRollsIndex, i]) + separator
    avgSpikeDurations[maxRollsIndex] += normalizedSpikeDurations[maxRollsIndex, i] * i

for i in range(totalSystems + 1):
    label = str(i) + ": "
    separator = "" if i >= maxRolls + 1 else ", "
    systemsDisabledStatStrings[successIndex] += label + formatProbAsPercent(normalizedSystemsDisabled[successIndex, i]) + separator
    avgSystemsDisabled[successIndex] += normalizedSpikeDurations[successIndex, i] * i
    systemsDisabledStatStrings[recoverableFailIndex] += label + formatProbAsPercent(normalizedSystemsDisabled[recoverableFailIndex, i]) + separator
    avgSystemsDisabled[recoverableFailIndex] += normalizedSpikeDurations[recoverableFailIndex, i] * i
    systemsDisabledStatStrings[catastrophicFailIndex] += label + formatProbAsPercent(normalizedSystemsDisabled[catastrophicFailIndex, i]) + separator
    avgSystemsDisabled[catastrophicFailIndex] += normalizedSpikeDurations[catastrophicFailIndex, i] * i
    systemsDisabledStatStrings[maxRollsIndex] += label + formatProbAsPercent(normalizedSystemsDisabled[maxRollsIndex, i]) + separator
    avgSystemsDisabled[maxRollsIndex] += normalizedSpikeDurations[maxRollsIndex, i] * i

print("== PUNCH DETAILS ==")
print("Stop after ", str(maxRolls), " rolls, round percentages to ", str(roundTo), " decimal places.")
print("Drive Rating: ", str(effectiveDriveRating), ", Drill Distance: ", str(drillDistance), " hexes, Spike Duration (days): ", str(round(spikeDuration, roundTo)), ", Total Systems: ", str(totalSystems))
print("Drill DC: ", str(drillDC), ", Int/Pilot Check Mod: ", str(intPilotMod), ", Spike Check Success Probability: ", formatProbAsPercent(spikeCheckSuccessProb))
print("Rutter Age: ", "Blind Punch" if rutterAge == None else str(rutterAge), ", course is being trimmed" if isTrimmingCourse else "", ", drill activation was rushed" if wasDrillActivationRushed else "")
print("")
print("== SUCCESS STATS ==")
print("Overall Prob: ", formatProbAsPercent(probs[outcomesListIndex][successIndex]))
print("Avg Duration (days)", str(round(avgSpikeDurations[successIndex] * spikeDuration, 1)))
#print("Duration Probs (days): ", spikeDurationStatStrings[successIndex])
print("Avg Systems Disabled", str(round(avgSystemsDisabled[successIndex], 1)))
#print("Systems Disabled Probs: ", systemsDisabledStatStrings[successIndex])
print("")
print("== RECOVERABLE FAIL STATS ==")
print("Overall Prob: ", formatProbAsPercent(probs[outcomesListIndex][recoverableFailIndex]))
print("Avg Duration (days)", str(round(avgSpikeDurations[recoverableFailIndex] * spikeDuration, 1)))
#print("Duration Probs (days): ", spikeDurationStatStrings[recoverableFailIndex])
print("Avg Systems Disabled", str(round(avgSystemsDisabled[recoverableFailIndex], 1)))
#print("Systems Disabled Probs: ", systemsDisabledStatStrings[recoverableFailIndex])
print("")
print("== CATASTROPHIC FAIL STATS ==")
print("Overall Prob: ", formatProbAsPercent(probs[outcomesListIndex][catastrophicFailIndex]))
print("Avg Duration (days)", str(round(avgSpikeDurations[catastrophicFailIndex] * spikeDuration, 1)))
#print("Duration Probs (days): ", spikeDurationStatStrings[catastrophicFailIndex])
print("Avg Systems Disabled", str(round(avgSystemsDisabled[catastrophicFailIndex], 1)))
#print("Systems Disabled Probs: ", systemsDisabledStatStrings[catastrophicFailIndex])
print("")
print("== MAX ROLLS STATS ==")
print("Overall Prob: ", formatProbAsPercent(probs[outcomesListIndex][maxRollsIndex]))
print("Avg Duration (days)", str(round(avgSpikeDurations[maxRollsIndex] * spikeDuration, 1)))
#print("Duration Probs (days): ", spikeDurationStatStrings[maxRollsIndex])
print("Avg Systems Disabled", str(round(avgSystemsDisabled[maxRollsIndex], 1)))
#print("Systems Disabled Probs: ", systemsDisabledStatStrings[maxRollsIndex])
print("")
print("== PROGRAM STATS ==")
print("Sum probs (should be 100%): ", formatProbAsPercent(probs[outcomesListIndex][successIndex] + probs[outcomesListIndex][recoverableFailIndex] + probs[outcomesListIndex][catastrophicFailIndex] + probs[outcomesListIndex][maxRollsIndex]))
print("Total time (s): ", timeDiff.total_seconds())
