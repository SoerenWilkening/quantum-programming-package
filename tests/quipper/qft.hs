{-# LANGUAGE BangPatterns #-}
{-# LANGUAGE Strict #-}
{-# LANGUAGE FlexibleInstances #-}
import Quipper
import Control.Monad (forM_, replicateM)
import System.Environment (getArgs)
import Quipper.Internal.Circuit
import System.CPUTime
import Control.DeepSeq
import System.Random (newStdGen)
import Quipper.Internal.Printing (gatecount_of_circuit, print_gatecount)
import Data.IORef
import Quipper.Internal.Circuit (Circuit)
import Quipper.Internal.Printing (gatecount_of_circuit, print_gatecount)
import Quipper.Internal.Printing (aggregate_gatecounts_of_bcircuit, print_gatecount)
--import QuipperLib.ResourceCounting

--main :: IO ()
--main = do
--  let n = 4
--
--  -- Create the circuit
--  let circ :: Circ [Qubit]
--      circ = do
--        qs <- replicateM n (qinit False)  -- allocate qubits
--
--        -- Apply gates (QFT/Deutsch example)
--        forM_ [0..n-2] $ \k -> do
--          let target = qs !! k
--          hadamard_at target
--          forM_ [k..n-2] $ \l -> do
--            let control = qs !! (l + 1)
--            rGate (l + 2) target `controlled` control
--
--        let target = qs !! (n-1)
--        hadamard_at target
--
--        -- Touch all qubits to force construction
--        mapM_ hadamard qs
--
--        return qs
--
--  -- Measure time (this will include forcing via the monad)
--  start <- getCPUTime
--  let !circ =
--  end <- getCPUTime
--  putStrLn $ "Circuit thunk creation time (does not include full construction): " ++ show (end - start)
--
--  -- Print the circuit afterward
--  print_simple ASCII circ

instance NFData Qubit where
  rnf q = q `seq` ()   -- force outer constructor (or define deeper if possible)

instance NFData a => NFData (Circ a) where
  rnf circ = circ `seq` ()   -- placeholder: depends how Circ is defined

-- declare deutsch_circuit function
deutsch_circuit :: Int -> Circ [Qubit]
deutsch_circuit i = do
--  start <- liftIO getCPUTime
  -- create the ancillae
  qubits <- replicateM i (qinit False)

  forM_ [0..i-2] $ \k -> do
    let target = (qubits !! k)
    hadamard_at target

    forM_ [k..i-2] $ \l -> do
      let control = (qubits !! (l + 1))
      rGate (l + 2) target `controlled` control

  let target = (qubits !! (i-1))
  hadamard_at target
--  end <- liftIO getCPUTime
--  putStrLn $ "t2: " ++ show (end - start) ++ "ps"
  return qubits


forceCircuit :: Int -> Circ [Qubit] -> IO ()
forceCircuit n circ =
  circ `deepseq` putStrLn ("Circuit " ++ show n ++ " fully evaluated!")



-- main function to call the whole program
main :: IO ()
main = do
  args <- getArgs
  let n = 500
  let nDefault = 500
  n <- case args of
    (nStr:_) -> return (read nStr :: Int)
    []       -> return nDefault

  start <- getCPUTime

--  _ <- run_generic_io gen 0 (deutsch_circuit n)
  let circ = deutsch_circuit n
  print_generic GateCount circ
--  (gatecount, _) <- run_generic GateCount (deutsch_circuit n)
  end <- getCPUTime
--  totRef <- newIORef 0
--  forM_ [0..10] $ \k -> do
--    s1 <- getCPUTime
--    print_generic GateCount circ
--    s2 <- getCPUTime
--    modifyIORef totRef (+ (s2 - s1))  -- increment total
--  tot <- readIORef totRef
--  let average = (fromIntegral tot :: Double) / 10.0  -- divide by 1
--  let diff = fromIntegral (end - start) - average

  putStrLn $ "t1: " ++ show (end - start) ++ "ps"
  return ()