# Cairo

This is a partially persistent file syncing utility. It's used to store versions of a directory structure in time that can be visited and explored, but not changed. You can't change your past.

It will also sync the directory with a server with a simple replace rule. However, if there's a version collision, a true timeline must be chosen. It's best to avoid this fate by syncing before modifying.

This code here is a prototype in Python to prove the concept and create a reference implementation to work off of to eventually create in Haskell (for experimentation) or C (for efficiency).

## Architecture

The main data structures are as follows:

```haskell
data FileType = Dir | Txt | Bin

type VerID = String

data Version = Version VerID UTCTime

data File = File {
  Name     :: Text,
  FileData :: Data.ByteString,
  Children :: [File],
  Type     :: FileType,
  ID       :: String,
  Mods     :: [Mod]
}

-- Modifications/Changes to the version
data Mod = Mod {
  Version :: Version,  -- Which version
  Field   :: String,   -- Which field changed?
  Value   :: Text      -- This could be anything. Not sure how to do this
}
```