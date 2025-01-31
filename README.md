# Spike-Drive Probabilities Calculator
*[Click here](https://oliverbaerbenson.dev/spike-drive-probabilities-calculator) to use the calculator.*

TL;DR: A program to calculate the probability of catastrophic failure for a roll which can recur in a tabletop roleplaying game.

### The situation
I am in a [Stars Without Number](https://en.wikipedia.org/wiki/Stars_Without_Number) game, in which we are looking to make some very risky faster-than-light jumps (spike drills). I would like to know the probability that we come out of these jumps in one piece.

### The problem
In this game, jumps are prone to mishaps, some of which are recursive. These mishaps force you to attempt the jump again, which can lead to more mishaps, which can force you to attempt the jump again, which can... and so on and so forth. I am not good enough at statistics to model this mathematically.

### The solution
This program brute forces the probabilities of success, recoverable failure, and catastrophic failure for any given jump to a depth of 100 recursions. If you are still rolling mishaps after 100 recursions, you might as well just take the catastrophic failure and have fun with it.
