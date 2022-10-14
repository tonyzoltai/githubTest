#!/usr/bin/env python

'''
experiment_5 - Compute a quasi-Pareto front on best prediction and smallest size in states, for FSM solutions evolving to
                recognise progressively more complex members of a family of languages, the "Universal Witness" languages of Brzozowski.
                (See uniwitness.py for reference.)

Classes:
    None.

Functions:
    complexophile_mutator - mutation operator for Moore Machines.  Sets a random transition arc, half the time to a new state (hence "complexophile"),
    and changes the ouput of a random state to a random value.

'''

__author__ = "Gabor 'Tony' Zoltai"
__copyright__ = "Copyright 2022, Gabor Zoltai"
__credits__ = ["Gabor Zoltai"]
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Tony Zoltai"
__email__ = "tony.zoltai@gmail.com"
__status__ = "Prototype"


# Parameters
INPUT_ALPHABET_SIZE = 3 # The Universal Witness languages use a three-symbol alphabet.



from copy import deepcopy

import numpy
from numpy.random import poisson
import logging
import optparse

import automata
import FSMScorer
import SMO_GP
from uniwitness import UniWitness
import countable

def complexophile_mutator(mm_parent: automata.CanonicalMooreMachine):

    # First, make a copy of the given parent object
    m = deepcopy(mm_parent)

    # Pick a random source state for an arc, an input label
    source_state = numpy.random.choice(m.state_count())
    input = numpy.random.choice(m.input_count())

    # Target is a new state half the time

    if numpy.random.choice(2) == 1:
        target_state = m.state_count()
        m.add_state()
    else:
        target_state = numpy.random.choice(m.state_count())

    # Change the arc
    m.set_arc(source_state, input, target_state)

    # Change the output of a random state to a random value
    state_to_change = numpy.random.choice(list(m.states()))
    new_output = numpy.random.choice(list(m.outputs()))
    m.set_output(state_to_change, new_output)
    #logging.debug("Mutant:")
    #logging.debug(m)
    return m

def poisson_repeat(f, poisson_lambda):
    '''Return a function that will repeatedly apply f to its input, determined by the Poisson distribution with parameter poisson_lambda (but at least once).'''
    def fun(x):
        r = x
        n = 1 + numpy.random.poisson(lam = poisson_lambda)
        #logging.debug("Repeating function %d times.", n)
        for _ in range(n):
            r = f(r)
        return r

    return fun

def randomly_repeated_application(f, k):
    '''Return a function to apply a function to its input k times.'''
    def fun(x):
        r = x
        for _ in range(k):
            r = f(r)
        return r

    logging.debug("Repeat will be for %d applications", k)
    
    return fun

class E5Scorer(FSMScorer.FSMScorer):
    '''A scorer for FSMs that uses a reference dictionary based on a changing subset of a regular language.'''
    def __init__(self, n, cmm) -> None:
        '''Create an FSMScorer of n strings.  These should be balanced between positive and negative examples
            for the language of the CanonicalMooreMachine cmm.  If the scoring table were not balanced, e.g.
            mostly negative examples, simple FSMs that just reject everything would be inappropriately favoured.'''
        super().__init__()

        d = dict()
        mr = automata.MooreMachineRun(cmm)
        positive = 0
        negative = 0

        for s in countable.all_words_from_alphabet(range(3)):
            mr.reset()
            mr.multistep(s)
            result = mr.output()
            #print(s, "result: ", result, "pos: ", positive, "neg: ", negative)
            if (positive >= negative and result == 0) \
            or (positive <= negative and result == 1):
                d[s] = result
                if result == 1:
                    positive += 1
                else:
                    negative += 1
                if positive + negative >= n:
                    break
        self.reference_dict = d

def create_scorer(table_size, cmm):

    logging.info("Maximal score: " + str(table_size))

    return E5Scorer(table_size, cmm)

def complexity_scorer(moore_machine: automata.MooreMachine):
    '''Returns an integer score for the complexity of a given Moore machine.  The lower the number of states, the higher the score.'''
    return -moore_machine.state_count()

# def dynamic_change(fitness_scorer: E5Scorer, change_per_gen):
#     '''Generator to periodically change the given fitness scorer, depending on the number of changes per generation (float).'''

#     change = 0
#     while True:
#         change += change_per_gen
#         # recalc = False
#         while change >= 1:
#             #recalc = True
#             change -= 1

#             fitness_scorer.reduce()
#             fitness_scorer.extend()
#             yield True

#         #yield recalc
#         yield False

def main(options, args):

    numpy.random.seed(options.SEED)

    logging.basicConfig(level=getattr(logging, options.LOGLEVEL.upper()),
                        format="%(asctime)s %(levelname)s: %(message)s")
    logging.info("Start of run")


    # Setup
    primitive = automata.CanonicalMooreMachine(input_count=INPUT_ALPHABET_SIZE)

    fitness_scorer = create_scorer(options.DICTSIZE, UniWitness(options.UNIWITNESS))
    logging.info("Longest scoring string: " + str(max([len(s) for s in fitness_scorer.reference_dict.keys()])))

    change_per_gen = options.CHANGE / 100 * fitness_scorer.table_size()

    # Run the SMO-GP algorithm for N cycles
    change = 0
    for i, g in enumerate(SMO_GP.SMO_GP(
                    initial_individuals={primitive},
                    mutator=poisson_repeat(complexophile_mutator, 1.0),
                    objectives=(fitness_scorer.score, complexity_scorer),
                    dynamic_change=None
                ).populations()):

        if options.INFOGENS >0 and i % options.INFOGENS == 0:
            logging.info("Generation " + str(i))
        if i >= options.GENERATIONS:
            break

    # Print the scoring dictionary
    logging.debug("Scoring table:")
    longest = max([len(s) for s in fitness_scorer.reference_dict.keys()])
    for length in range(longest + 1):
        for s in [ x for x in fitness_scorer.reference_dict.keys() if len(x) == length]:
                logging.debug("%s %s", s, fitness_scorer.reference_dict[s])

    # Print the resulting estimate of the Pareto front
    for individual, scores in g:
        logging.info("The following automaton scored %d with %d states:\n%s", scores[0], -scores[1] ,str(individual))
        print(-scores[1], scores[0], sep=",")

    logging.info("End of run")


# Self-test, to be executed for option -t
# Can't use unittest the way I want to, so writing it myself

def myAssertEqual(a,b):
    if a == b:
        print("Test case successful.")
    else:
        print("Test case failed.")
        print("a:")
        print(a)
        print("b:")
        print(b)

def selfTest():
        e = E5Scorer(100,UniWitness(3))
        myAssertEqual(100, len(e.reference_dict.keys()))
        pos = len([s for s in e.reference_dict if e.reference_dict[s] == 1])
        myAssertEqual(pos, 50)
        myAssertEqual(e.reference_dict[0,0,1], 1)


if __name__ == "__main__":

    parser = optparse.OptionParser(("Usage: %prog [OPTION]...\n"
                                    "Evolve FSMs to recognise a randomised language, using SMO-GP, output pairs of recognition score and FSM size."))
    parser.add_option("-l", "--log", choices = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
                    action="store", dest="LOGLEVEL", default="DEBUG",
                    help="set minimum logging level to LOGLEVEL; one of DEBUG, INFO, WARNING, ERROR or CRITICAL (default: %default)")
    parser.add_option("-g", "--generations", type="int", action="store", dest="GENERATIONS", default=1000,
                    help="specify the number of generations to run for (default: %default)")
    parser.add_option("-i", "--inform", type="int", action="store", dest="INFOGENS", default=10,
                    help="if not zero, produce a message as a sign of life every INFOGENS generations; ignored if logging level is higher than INFO (default: %default)")
    parser.add_option("-s", "--seed", type="int", action="store", dest="SEED", default=0,
                    help="specifies the starting seed of the random number generator, so runs are repeatable (default: %default)")
    parser.add_option("-d", "--dict", type="int", action="store", dest="DICTSIZE", default=6,
                    help="set the size of the dictionary of samples in the randomised language (default: %default)")
    parser.add_option("-c", "--change", type = "float", action="store", dest="CHANGE", default=0.0,
                    help="percentage of fitness reference table to change per generation (default: %default)")
    parser.add_option("-t", "--test", action="store_true", dest="SELFTEST",
                    help="executes a self test")
    parser.add_option("-u", "--uniwitness", type="int", action="store", dest="UNIWITNESS", default=3,
                    help="sets the number of the Universal Witness language to use at start (default: %default)")

    (options, args) = parser.parse_args()

    if hasattr(options, "SELFTEST") and options.SELFTEST:
        selfTest()
    else:
        main(options, args)
